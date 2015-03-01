#!/usr/bin/python2.4 -u

# First attempt to write a bugs query parser for less structured text queries.
# This one will have hacks made along the way as I understand more of what kind
# of queries people are likely to submit. From what we learn from this, we can 
# do a better second iteration later on. -- shirald/September, 2014 

import os, sys, re, shlex, time, calendar, urllib

# -- add QA lib path if not added by a/the calling script
if not ( '/math/Admin/sqa/lib/python' in sys.path or '/math/Admin/sqa/lib/python/Temp' in sys.path ):
   sys.path.insert(0, '/math/Admin/sqa/lib/python' )

import Databases, Bugs

try:             USER = os.environ['REMOTE_USER']
except KeyError: USER = os.environ['USER']
except KeyError: USER = os.environ['LOGNAME']

QUERY = ''        # -- The original query
HOLE  = '____'    # -- word(s) parsed out here; hence, discontinuity.
ATTRIBUTES  = {}  # -- { 'primarydeveloper':'PrimaryDeveloper', .... }
VALUE_INDEX = {}  # -- e.g. { 'open':'Status', 'Mathematica':'Program', 'beforeyesterday':'date', '10.0.0':'version', 'xyz':'None', ... }
KNOWN_IDS   = { 'SeeAlso':['TAGMOVE_REQUESTED','TAG_MOVED', 'TAGMOVE_REJECTED'] } # -- known IDs; mostly things that go in an out of db


def fill_attribute_name_dict( dbc ):
    """
    Fill ATTRIBUTES dictionary: { 'qacontact'=>'QAContact', ... }
    """
    cur = dbc.cursor()
    q_db_attr = "select value from attribute_value_index where attribute='attribute'"
    cur.execute( q_db_attr )

    rows = cur.fetchall()
    cur.close()

    for row in rows: 
        attr_name       = row['value']
        attr_name_lower = attr_name.lower()
        ATTRIBUTES[ attr_name_lower ] = attr_name


def normalize_free_text_query_phrase( word_ar ):
    """
    simply rearrange the description of free text query phrases such as
    summary:<keywords>. This has only few lines, but prevents having to have
    repeated code
    """
    query_phrase = ' '.join( word_ar )
    query_phrase = re.sub( r'(summary|problem|description|body)\s*~\s*',           r'\1:~',   query_phrase ) # -- <attr>~ => <attr>:~
    query_phrase = re.sub( r'(summary|problem|description|body)\s*(:?)\s*(~?)\s*', r'\1\2\3', query_phrase ) # -- compact <attr> : and ~

    return query_phrase


def resolve_free_text_attrs( query ):
    """
    separate summary: problem: description: phrases. Any of these should end the query or
    be followed by '--' or a new attribute specification given in the form 'attribute:'
    """
    free_text_attr   = ('summary', 'problem', 'description', 'body')
    regular_attr     = filter( lambda x: x not in free_text_attr, ATTRIBUTES.keys() )
    reg_attr_aliases = ( 'reporter', 'from', 'tester', 'devel', 'developer', 'manager', 'body' ) 
    all_attr_words   = ATTRIBUTES.keys()
    all_attr_words.extend( reg_attr_aliases )

    all_attr_reg_exp  = eval( "r'(?i)(^|\s)(" + '|'.join(all_attr_words) + ")(\s*[:~])'" ) 
    query = re.sub( all_attr_reg_exp, r'\1\2 \3 ', query ) # -- put spaces on either side of : or ~ after attr word

    elems = re.split( r'\s+', query ) 

    temp, resolved, rest, collect = [], [], [], False
    for i in range(len(elems)):
        elem_lower = elems[i].lower()

        if elem_lower in free_text_attr:
            attr_type = 'FREE_TEXT'
        elif elem_lower in regular_attr or elem_lower in reg_attr_aliases:
            attr_type = 'REGULAR'
        else:
            attr_type = ''

        try:               separator_next = (elems[i+1] == ':' or elems[i+1] == '~')
        except IndexError: separator_next = False
   
        if attr_type == 'FREE_TEXT' and separator_next: 
            collect = True
            rest.append( HOLE )

        if collect: 
            # -- end of free text search phrase and temp has collected some
            if temp and (elem_lower == '--' or ((attr_type == 'FREE_TEXT' or attr_type == 'REGULAR') and separator_next)):
                resolved.append( normalize_free_text_query_phrase(temp) )

            if elem_lower == '--':
                collect = False
                temp = []
            elif attr_type == 'FREE_TEXT' and separator_next:
                temp = [elem_lower]
            elif attr_type == 'REGULAR' and separator_next:
                collect = False
                temp = []
                rest.append( elems[i] )
            else:
                temp.append( elems[i] )
        else:
            rest.append( elems[i] )

    if collect and temp: 
        resolved.append( normalize_free_text_query_phrase(temp) )

    query_rest = ' '.join( rest )

    return resolved, query_rest


def translate_string_nums( query ):
    """
    translate string specification of small numbers in date/time specifications 
    people are likely to type in to their numerical counter parts.
    e.g. August 16th => August 16, 
         Sep 5th => Sep 5 (upto 12th)
         last three weeks => last 3 weeks
    """
    long_month_pattern  = '(January|February|March|April|May|June|July|August|September|October|November|December)'
    short_month_pattern = '(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'

    # -- e.g. Apr[il] 16th => Apr[il] 16
    query = re.sub( eval("r'"+long_month_pattern +"(\s*\d+\s*)(st|nd|rd|th)\\b'"), r'\1\2', query )
    query = re.sub( eval("r'"+short_month_pattern+"(\s*\d+\s*)(st|nd|rd|th)\\b'"), r'\1\2', query )

    # -- e.g. Sep[tember] seventh => Sep[tember] 7
    def func1(m, dict): g = m.groups(); return  g[0] + ' ' + str(dict[g[1]])
    dict1    = { 'first':1, 'second':2, 'third':3, 'fourth':4, 'fifth':4, 'sixth':6, 'seventh':7, 'eighth':8, 'ninth':9, 'tenth':10, 'eleventh':11, 'twelfth':12 }
    reg_exp1 = eval( "r'\\b"+long_month_pattern +"\s*(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth)\\b'" )
    reg_exp2 = eval( "r'\\b"+short_month_pattern+"\s*(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth)\\b'" )
    query    = re.sub( reg_exp1, lambda m: func1(m, dict1), query )
    query    = re.sub( reg_exp2, lambda m: func1(m, dict1), query )

    # -- e.g. last three weeks => last 3 weeks
    dict3    = { 'one':1, 'two':2, 'couple':2, 'three':3, 'four':4, 'five':5, 'six':6, 'seven':7, 'eight':8, 'nine':9, 'ten':10, 'eleven':11, 'twelve':12 }
    reg_exp3 = eval( "r'\\blast\s+(one|two|couple|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(day|week|month|year)(s?)\\b'" )
    def func3(m, dict): g = m.groups(); return 'last '+ str(dict[g[0]]) + ' ' + g[1]+g[2]
    query    = re.sub( reg_exp3, lambda m: func3(m, dict3) , query )

    return query


def normalize_year( year, month ):
    """
    helper funtion for format_date()
    This sets the year if year is not explicitly set.
    If the month is in the future in this year, the year
    will be set to last year; otherwise, this year
    """
    if year is not None:
        year = str( year )
        if len(year) == 4:  # -- all 4 digits given
            return year
        elif len( year ) == 2: # -- only 2 digits given
            year_num = int( year )
            if year_num < 50: year_num += 2000  
            else            : year_num += 1900
            return str( year_num )

    this_year  = time.strftime( "%Y", time.localtime() )
    last_year  = str( int(this_year) - 1 )
    this_month = time.strftime( "%m", time.localtime() )

    if isinstance( month, int ) or month.isdigit(): # -- e.g. 9 or '09'
        month_num = int( month )
    else: # -- month string
        try: # -- e.g. Jan
            month_num = time.strptime( month, '%b' ).tm_mon
        except ValueError: # -- e.g. January 
            month_num = time.strptime( month, '%B' ).tm_mon

    if month_num > int( this_month ):
        year = str( last_year )
    else:
        year = str( this_year )

    return year


def format_date( oMatch, format_id_num ):
    """
    helper function for translate_dates(): format some forms of date specifications.
    e.g.
      Aug[ust] 7[, 2014] => 20140807
      in Feb[ruary][, 2014] => 20140201-20140228
      from July 1 to 10[, 2014] => from20140701to20140710
      between June 25 and July 5[, 2014] => between20140625and20140705
    """
    if format_id_num % 2 == 1: # -- e.g. January 1[, 2014] -- odd format_id_num
        date_format = "%B %d, %Y"
    else:                      # -- e.g. Jan 1[, 2014] -- even format_id_num
        date_format = "%b %d, %Y"

    if format_id_num in (1, 2): # -- on day
        month, day, year = oMatch.group(1), oMatch.group(2), oMatch.group(4)
        year = normalize_year( year, month )
        sDate = time.strptime( month + ' ' + day + ', ' + year, date_format )
        return time.strftime( "%Y%m%d", sDate )
    elif format_id_num in (3, 4): # -- in month
        month, year = oMatch.group(1), oMatch.group(3)
        year = normalize_year( year, month )

        sDate1 = time.strptime( month + ' 01, ' + year, date_format )
        first_day, last_day = calendar.monthrange( sDate1[0], sDate1[1] )
        sDate2 = time.strptime( month + ' ' + str(last_day) + ', ' + year, date_format )

        date_range_spec = time.strftime( "%Y%m%d", sDate1 ) + '-' + time.strftime( "%Y%m%d", sDate2 )
        return date_range_spec
    elif format_id_num in (5, 6): # -- same year: e.g. from June 30 to July 5[, 2014]
        start_str, start_month, start_day, end_str, end_month, end_day, dummy, year = oMatch.groups()
        year = normalize_year( year, start_month )

        start_date = time.strptime( start_month + ' ' + start_day + ', ' + year, date_format )
        end_date   = time.strptime( end_month   + ' ' + end_day   + ', ' + year, date_format )

        date_range_spec =  start_str + time.strftime("%Y%m%d",start_date) + end_str + time.strftime("%Y%m%d",end_date)
        return date_range_spec
    elif format_id_num in (7, 8): # -- same month: e.g. from July 2 to 10[, 2014]
        start_str, month, start_day, end_str, end_day, dummy, year = oMatch.groups()
        year = normalize_year( year, month )

        start_date = time.strptime( month + ' ' + start_day + ', ' + year, date_format )
        end_date   = time.strptime( month + ' ' + end_day   + ', ' + year, date_format )

        date_range_spec =  start_str + time.strftime("%Y%m%d",start_date) + end_str + time.strftime("%Y%m%d",end_date)
        return date_range_spec
    elif format_id_num in (11, 12): # -- same month: e.g. from Sep[tember] 2[, 2014]
        start_str, month, start_day, dummy, year = oMatch.groups()
        year = normalize_year( year, month )

        start_date = time.strptime( month + ' ' + start_day + ', ' + year, date_format )
        date_range_spec =  start_str + time.strftime("%Y%m%d",start_date)
        return date_range_spec
    elif format_id_num == 9: # -- e.g. last three weeks
        count_dict = { 'one':1, 'two':2, 'couple':2, 'three':3, 'four':4, 'five':5, 'six':6, 'seven':7, 'eight':8, 'nine':9, 'ten':10, 'eleven':11, 'twelve':12 }
        last_this, str_num, cal_period = oMatch.group(2), oMatch.group(3), oMatch.group(4)
        return last_this + str(count_dict[str_num.lower()]) + cal_period + 's'
    elif format_id_num == 13: # -- e.g. 2014-04-05 or 2014/4/5
        year, month, date = oMatch.groups()
        if len(month) == 1: month = '0' + month
        if len(date)  == 1:  date = '0' + date
        return year + month + date
    elif format_id_num == 14: # -- e.g. 9/15/2014, 9/15/14, or 9/15
        month, date, dummy, year = oMatch.groups()
        if len(month) == 1: month = '0' + month
        if len(date)  == 1:  date = '0' + date
        year = normalize_year( year, month )
        return year + month + date
    elif format_id_num in (15, 16, 17, 18, 19, 20): # -- before(15,16)/since(17,18)/after(19,20) month
        month, year = oMatch.group(1), oMatch.group(3)
        year = normalize_year( year, month )
        sDate1 = time.strptime( month + ' 01, ' + year, date_format )
        first_day, last_day = calendar.monthrange( sDate1[0], sDate1[1] )

        if format_id_num in (19,20): day = last_day
        else                       : day = '01'
        date_limit = time.strptime( month + ' '+ str(day) +', ' + year, date_format )
        date_limit_str = time.strftime( "%Y%m%d", date_limit )

        if   format_id_num in (15, 16): prefix = 'before'
        elif format_id_num in (17, 18): prefix = 'since'
        elif format_id_num in (19, 20): prefix = 'after'
        return prefix+date_limit_str
    else:
        raise RuntimeError("Invalid date format id number")
    

def translate_dates( query ):
    """
    translate various commonly typed date formats to one that findbugs can handle
    """
    this_year  = time.strftime( "%Y", time.localtime() )

    query = translate_string_nums( query )
    query = re.sub( r'\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b',          lambda m: format_date(m,13), query ) # -- e.g 2013-04-07 | 2013/4/7 YYYY/[M]M/[D]D 
    query = re.sub( r'\b(\d{1,2})[/\-](\d{1,2})([/\-](\d{4}|\d{2})|)\b', lambda m: format_date(m,14), query ) # -- e.g. 9/15/2014, 9/15/14, or 9/15

    last_weekday1 = r'(?i)\blast\s*(sunday|monday|tuesday|wednesday|thursday|friday|saturday)'
    query = re.sub( last_weekday1, lambda m: Databases.GetLastWeekday(m.group(1)), query ) # -- last Monday => YYYYMMDD

    last_weekday2 = r'(?i)\b(sunday|monday|tuesday|wednesday|thursday|friday|saturday)'
    query = re.sub( last_weekday2, lambda m: Databases.GetLastWeekday(m.group(1)), query ) # -- Monday (last assumed) => YYYYMMDD

    def f_year(m):
        g = m.groups()
        return g[0]+g[1]+'0101-'+g[0]+g[1]+'1231'

    query = re.sub( r'\bon\s*(\d{8})\b', r'\1',  query ) # -- on <Data>
    query = re.sub( r'\bin\s+(19|20)(\d\d)\b', lambda m: f_year(m),  query )    # -- in <Year>
    query = re.sub( r'(?i)\b(|in\s+|within\s+)(|the\s+)(last)\s*(\d+)\s*(day|week|month|year)s?\b', r'\3\4\5s', query ) # -- last 3 weeks
    query = re.sub( r'(?i)\b(|in\s+|within\s+)(|the\s+)(last|this)\s*(week|month|year)s?\b',        r'\3\4',    query ) # -- last week

    # -- weekday names are no longer needed here, but won't hurt
    weekday_pattern_d8 = '(sunday|monday|tuesday|wednesday|thursday|friday|saturday|\d{8})'
    query = re.sub( eval( "r'(?i)\\b(from|since|before|after)\s*(last|)\s*"+weekday_pattern_d8+"\\b'" ), r'\1\2\3', query ) # -- since last Friday
    query = re.sub( eval( "r'(?i)\\bon\s*or\s*(before|after)\s*(last|)\s*"+weekday_pattern_d8+"\\b'" ), r'onor\1\2\3', query ) # -- on or before last Friday
    query = re.sub( eval( "r'(?i)\\bon\s*(last|)\s*"+weekday_pattern_d8+"\\b'" ), r'\1\2', query ) # -- on last Friday
    query = re.sub( eval( "r'(?i)\\b(last)\s*"+weekday_pattern_d8+"\\b'" ), r'\1\2', query ) # -- e.g. last Sunday

    long_month_pattern  = '(January|February|March|April|May|June|July|August|September|October|November|December)'
    short_month_pattern = '(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'

    query = re.sub( eval("r'(?i)(\d+)\s?(?:st|nd|rd|th)\s+"+long_month_pattern+"'"),  r'\2 \1', query ) # -- e.g. 10th October => October 10
    query = re.sub( eval("r'(?i)(\d+)\s?(?:st|nd|rd|th)\s+"+short_month_pattern+"'"), r'\2 \1', query ) # -- e.g. 10th Oct => Oct 10

    same_year_long = eval( "r'(?i)\\b(from|between)\s+"+long_month_pattern+"\s*(\d{1,2})\s+(to|and)\s+"+long_month_pattern+"\s+(\d{1,2})([,\s]+(\d{4})|)\\b'" )
    query = re.sub( same_year_long, lambda m: format_date(m,5), query ) # -- e.g. from January 25 to February 5[, 2014]

    same_year_short = eval( "r'(?i)\\b(from|between)\s+"+short_month_pattern+"\s*(\d{1,2})\s+(to|and)\s+"+short_month_pattern+"\s+(\d{1,2})([,\s]+(\d{4})|)\\b'" )
    query = re.sub( same_year_short, lambda m: format_date(m,6), query ) # -- e.g. from January 25 to February 5[, 2014]

    same_month_long = eval( "r'(?i)\\b(from|between)\s+"+long_month_pattern+"\s*(\d{1,2})\s+(to|and)\s+(\d{1,2})([,\s]+(\d{4})|)\\b'" )
    query = re.sub( same_month_long, lambda m: format_date(m,7), query ) # -- e.g. from January 1 to 10[, 2014]

    same_month_short = eval( "r'(?i)\\b(from|between)\s+"+short_month_pattern+"\s*(\d{1,2})\s+(to|and)\s+(\d{1,2})([,\s]+(\d{4})|)\\b'" )
    query = re.sub( same_month_short, lambda m: format_date(m,8), query ) # -- e.g. from Jan 1 to 10[, 2014]

    from_month_long = eval( "r'(?i)\\b(from|since)\s+"+long_month_pattern+"\s*(\d{1,2})([,\s]+(\d{4})|)\\b'" )
    query = re.sub( from_month_long, lambda m: format_date(m,11), query ) # -- e.g. from January 1[, 2014]

    from_month_short = eval( "r'(?i)\\b(from|since)\s+"+short_month_pattern+"\s*(\d{1,2})([,\s]+(\d{4})|)\\b'" )
    query = re.sub( from_month_short, lambda m: format_date(m,12), query ) # -- e.g. from Jan 1[, 2014]

    date_with_month_long = eval( "r'(?i)\\b"+long_month_pattern+"\s*(\d{1,2})([,\s]+(\d{4})|)\\b'" )
    query = re.sub( date_with_month_long, lambda m: format_date(m,1), query ) # -- e.g. January 1[, 2014]

    date_with_month_short = eval( "r'(?i)\\b"+short_month_pattern+"\s*(\d{1,2})([,\s]+(\d{4})|)\\b'" )
    query = re.sub( date_with_month_short, lambda m: format_date(m,2), query ) # -- e.g. Jan 1[, 2014]

    before_month_long = eval( "r'(?i)\\b(?:before|till|until|up\s+until)\s+(?:last\s+|)"+long_month_pattern+"([,\s]+(\d{4})|)\\b'" )
    query = re.sub( before_month_long, lambda m: format_date(m,15), query ) # -- e.g. before last January[, 2014]

    before_month_short = eval( "r'(?i)\\b(?:before|till|until|up\s+until)\s+(?:last\s+|)"+short_month_pattern+"([,\s]+(\d{4})|)\\b'" )
    query = re.sub( before_month_short, lambda m: format_date(m,16), query ) # -- e.g. before last Jan[, 2014]

    since_month_long = eval( "r'(?i)\\b(?:since|from)\s+(?:last\s+|)"+long_month_pattern+"([,\s]+(\d{4})|)\\b'" )
    query = re.sub( since_month_long, lambda m: format_date(m,17), query ) # -- e.g. since last January[, 2014]

    since_month_short = eval( "r'(?i)\\b(?:since|from)\s+(?:last\s+|)"+short_month_pattern+"([,\s]+(\d{4})|)\\b'" )
    query = re.sub( since_month_short, lambda m: format_date(m,18), query ) # -- e.g. since last Jan[, 2014]

    after_month_long = eval( "r'(?i)\\bafter\s+(?:last\s+|)"+long_month_pattern+"([,\s]+(\d{4})|)\\b'" )
    query = re.sub( after_month_long, lambda m: format_date(m,19), query ) # -- e.g. after last January[, 2014]

    after_month_short = eval( "r'(?i)\\bafter\s+(?:last\s+|)"+short_month_pattern+"([,\s]+(\d{4})|)\\b'" )
    query = re.sub( after_month_short, lambda m: format_date(m,20), query ) # -- e.g. after last Jan[, 2014]

    in_month_long = eval( "r'(?i)\\b(?:in|last|in\s+last)\s+"+long_month_pattern+"([,\s]+(\d{4})|)\\b'" )
    query = re.sub( in_month_long, lambda m: format_date(m,3), query ) # -- e.g. in|last|in last January[, 2014]

    in_month_short = eval( "r'(?i)\\b(?:in|last|in\s+last)\s+"+short_month_pattern+"([,\s]+(\d{4})|)\\b'" )
    query = re.sub( in_month_short, lambda m: format_date(m,4), query ) # -- e.g. in|last|in last Jan[, 2014]

    num_pattern = '(one|two|three|four|five|six|seven|eight|nine|ten)'
    period_with_string_num = eval( "r'(?i)\\b(|in\s+|within\s+)(last)\s*"+num_pattern+"\s*(day|week|month|year)s?\\b'" ) 
    query = re.sub( period_with_string_num, lambda m: format_date(m,9), query ) # -- e.g. last three weeks

    query = re.sub( r'(?i)\b(between|from)\s*(today|yesterday|\d{8})\s*(and|to)\s*(today|yesterday|\d{8})\b', r'\1\2\3\4', query )
    query = re.sub( r'(?i)\bon\s*or\s*(before|after)\s*(today|yesterday|\d{8})\b', r'onor\1\2', query )
    query = re.sub( r'(?i)\b(before|after|lt|le|gt|ge)\s*(today|yesterday|\d{8})\b', r'\1\2', query )
    query = re.sub( r'(?i)(<|<=|>=|>)\s*(today|yesterday|\d{8})\b', r'\1\2', query )
    query = re.sub( r'(?i)\bon\s*(today|yesterday|\d{8})\b', r'\1', query )

    query_cs = re.sub( r'(?i)(today|yesterday|\d{8})\s*(,|and|or)\s*(today|yesterday|\d{8})\b', r'\1,\3', query )
    while query_cs != query: # -- comma separate dates
        query = query_cs
        query_cs = re.sub( r'(?i)(today|yesterday|\d{8})\s*(,|and|or|\s)\s*(today|yesterday|\d{8})\b', r'\1,\3', query )
    query = query_cs

    # --  between<date1>,<date2> => between<date1>and<date2>, <date1> - <date2> => <date1>-<date2>
    query = re.sub( r'(?i)between\s*(today|yesterday|\d{8})\s*,\s*(today|yesterday|\d{8})', r'between\1and\2', query )
    query = re.sub( r'(?i)(today|yesterday|\d{8})\s*\-\s*(today|yesterday|\d{8})',          r'\1-\2',          query )

    return query


def translate_basic( query ):
    """
    do basic translations such as devel,developer => PrimaryDeveloper, 
    func area => FunctionalArea, Bugs => ReportType:Bug etc. Basically, aliases
    and/or those that are ok to transform before trying contaction and 
    value index look up.
    """
    # -- \b won't work for every case (e.g. to avoig matching':'). 
    # -- Care should be take to see if it's a \s, : or ,

    # -- some aliases
    # -- DEVEL -- try to move here as much aliases as possible from translate_pattern() 
    query = re.sub( r'(?i)\bmma\b', r'Mathematica', query ) # -- mma => Mathematica
    query = re.sub( r'(?i)(^|\s)WS(\s|$)',    r'\1Mathematica\2', query ) # -- WS => Mathematica
    query = re.sub( r'(?i)\bWolfram\s*System\b',  r'Mathematica', query ) # -- Wolfram System => Mathematica

    query = re.sub( r'(?i)(^|\s)WL(\s|$)',     r'\1Mathematica Kernel\2', query ) # -- WL => Mathematica Kernel
    query = re.sub( r'(?i)\bWolfram\s*Language\b', r'Mathematica Kernel', query ) # -- Wolfram Language => Mathematica Kernel

    query = re.sub( r'(^|\s)WA(\s|$)', r'\1WolframAlpha\2', query ) # -- WA  => WolframAlpha
    query = re.sub( r'(^|\w\s+|[=:,]\s*)M\-(\s+\w|\s*,|$)', r'\1Mathematica\2', query ) # -- M- (case sensitive)=> Mathematica
    query = re.sub( r'(?i)\bwfp\b', r'WolframFinancePlatform', query )
    query = re.sub( r'(?i)(^|\w\s+|[=:,]\s*)(?:wolfram\s*alpha|alpha)(\s+\w|\s*,|$)', r'\1WolframAlpha\2', query ) # -- should preserve t-alpha-.* etc.

    query = re.sub( r'(?i)(Platforms?\s*Affected)', r'PlatformAffected', query ) # -- Platforms Affected => PlatformAffected
    query = re.sub( r'(?i)(?:Platforms?\s+(?:is\s+|are\s+|)(Linux|Windows|Mac|OSX))', r'PlatformAffected is \1', query ) # -- Platforms are => PlatformAffected
    query = re.sub( r'(?i)(?:broken\s+on\s+(Linux|Windows|Mac|OSX))', r'bugs PlatformAffected \1', query ) # -- broken on Winodws => bugs on Windows

    query = re.sub( r'(?i)(^|\s)32\s*bit\s*Linux(\s|$)',   r'\1Linux-x86\2',      query ) # -- 32|64 bit Linux|Windows => Linux-x86-64, etc.
    query = re.sub( r'(?i)(^|\s)64\s*bit\s*Linux(\s|$)',   r'\1Linux-x86-64\2',   query ) 
    query = re.sub( r'(?i)(^|\s)32\s*bit\s*Windows(\s|$)', r'\1Windows-x86\2',    query )
    query = re.sub( r'(?i)(^|\s)64\s*bit\s*Windows(\s|$)', r'\1Windows-x86-64\2', query ) 
    query = re.sub( r'(?i)(^|\s)(?:32\s*bit\s*(?:OSX|Mac))(\s|$)',      r'\1MacOSX-x86\2', query ) # -- 32 bit OSX|Mac  => MacOSX-x86
    query = re.sub( r'(?i)(^|\s)(?:(?:64\s*bit\s*|)(?:OSX|Mac))(\s|$)', r'\1MacOSX-x86-64\2', query ) # -- OSX|Mac  => MacOSX-x86-64

    query = re.sub( r'(?i)\bbranch\s+name(\s)', r'Branch\1', query ) # -- branch name => Branch

    # -- translated aliases of VersionReported and ResolutionVersion. 
    # -- don't translate phrases such as "resolved in"; leave them for action translation
    query = re.sub( r'(?i)\breported\s*version\b', r'VersionReported', query )
    query = re.sub( r'(?i)\b(?:version\s*resolved|resolved\s*version)\b', r'ResolutionVersion', query )

    # -- translate lately and recently
    query = re.sub( r'(?i)\b(open|filed|reported|resolved|resolve\s*tested|closed)\s+(?:recently|lately)\b', r'\1 last30days', query )
    query = re.sub( r'(?i)\b(?:recently|lately)\s+(open|filed|reported|resolved|resolve\s*tested|closed)\b', r'\1 last30days', query )

    query = re.sub( r'(?i)(^|\s)all(\s|$)', r'\1Resolution:all\2', query ) # -- remove Resolution:!Withdrawn if 'All' is searched

    # -- 'front end'=>'Front-end'
    if re.search( r'(?i)(wolfram\s*finance\s*platform|wfp)', QUERY ):
        query = re.sub( r'(?i)\bfront[\s\-]*end\b', r'FrontEnd', query ) 
    else:
        query = re.sub( r'(?i)\bfront[\s\-]*end\b', r'Front-end', query ) 

    # -- put spaces around '=' and '!=' so as to make them separate tokens
    query = re.sub( r'(?i)([\w\d])(=|!=|=!)([\w\d])', r'\1 \2 \3', query )

    # -- various ways people target a particular version
    query = re.sub( r'(?i)\s+(?:for|in|on)\s+(V?[\d\.]+)', r' in \1', query )

    # -- take "(open|resolved|closed) [upto two words (no 'by')] <report_type>" as a segment and set status as \1
    query = re.sub( r'(?i)\bnon[\s\-]+(open|resolved|closed)\s+((?:\w+\s+){0,2}(?:bug|suggestion|feature|hang|crash|report)(?:e?s\+?|\s+reports))', r'Status:!\1 \2', query ) 
    query = re.sub( r'(?i)\b(open|resolved|closed)\s+(?!by)((?:\w+\s+){0,2}(?:bug|suggestion|feature|hang|crash|report)(?:e?s\+?|\s+reports))', r'Status:\1 \2', query ) 

    # -- common negated report types
    query = re.sub( r'(?i)\breport\s+type\s+is\s+not\s+(bug|suggestion|feature|hang|crash)\b', r'ReportType:!\1', query ) # -- report type is not bug
    query = re.sub( r'(?i)\b(is|are)\s+not\s+(bug|suggestion|feature|hang|crash)e?s?\b',       r'ReportType:!\2', query ) # -- is not bug
    query = re.sub( r'(?i)\bnon(\s+|\-)(bug|suggestion|feature)s?\b',                          r'ReportType:!\2', query ) # -- non bugs

    # -- common non negated report types
    query = re.sub( r'(?i)(^|\w\s+)((bug|suggestion|feature|hang|crash)\s+reports)\b',    r'\1ReportType:\3',  query ) # -- bug reports ...
    query = re.sub( r'(?i)(^|\w\s+)((report|bug|suggestion|feature|hang|crash)e?s?)\s+(on|in)\s+\b', r'\1\2 ', query ) # -- bugs in ...
    query = re.sub( r'(?i)(^|\w\s+)(suggestion|feature|hang|crash)e?s?\b',                r'\1ReportType:\2' , query ) # -- bugs

    query = re.sub( r'(?i)(^|\s)bugs\+(\s|$)', r'\1ReportType:Bug,Suggestion\2', query ) # -- bugs+ => ReportType:Bug,Suggestion (should come before)
    query = re.sub( r'(?i)(?<!by)(^|\s+)bugs', r'\1ReportType:bug', query ) # -- bugs => ReportType:Bug, but spare 'by bugs'

    # -- DEVEL experimental: e.g. non Integrate => !Integrate
    query = re.sub( r'(?i)\bnon(\s+|\-)', r'!',   query ) 

    query = re.sub( r'(?i)\b(I|me)\b',           USER,      query ) # -- self references (e.g. shirald)
    query = re.sub( r'(?i)\b(my|mine|myself)\b', USER+"'s", query ) # -- self references (e.g. shirald's)

    query = re.sub( r'(?i)\'s\b', ' '+HOLE, query ) # -- discontinuity after 's
    query = re.sub( r'(?i),\s*(and|or|&)\b', ',', query ) # ', and' => ','

#   query = re.sub( r'(?i)\bp[:\s]*(\d)\b', r'Priority \1', query ) # -- p1,2 => Priority 1,2
    query = re.sub( r'(?i)\bp[:\s]*(\d)[\s,]*\b', r'Priority \1 ', query ) # -- p1,2 => Priority 1,2

    query = re.sub( r'(?i)\b(priority[\s:]+)zero\b',  r'\1 0', query )
    query = re.sub( r'(?i)\b(priority[\s:]+)one\b',   r'\1 1', query )
    query = re.sub( r'(?i)\b(priority[\s:]+)two\b',   r'\1 2', query )
    query = re.sub( r'(?i)\b(priority[\s:]+)three\b', r'\1 3', query )
    query = re.sub( r'(?i)\b(priority[\s:]+)four\b',  r'\1 4', query )
    query = re.sub( r'(?i)\b(priority[\s:]+)five\b',  r'\1 5', query )

    query = re.sub( r'(?i)\bpending\s+tag\s*moves\b',             r'TAGMOVE_REQUESTED', query ) 
    query = re.sub( r'(?i)\btag\s*move\s+(requested|requests)\b', r'TAGMOVE_REQUESTED', query ) 
    query = re.sub( r'(?i)\btag\s*(moved|moves)\b',               r'TAG_MOVED',         query ) 
    query = re.sub( r'(?i)\btag\s*move\s+(rejected|rejects)\b',   r'TAGMOVE_REJECTED',  query ) 

    query = re.sub( r'(?i)\b(unknown|missing|unclassified|undefined|undef)\b', 'none',   query ) # -- unset values
    query = re.sub( r'(?i)\bthat\s+are\s+not\s+(open|resolved|closed)\b', r'Status:!\1', query ) 
    query = re.sub( r'(?i)\bthat\s+are\s+(open|resolved|closed)\b',       r'Status:\1',  query ) 

    query = re.sub( r'(?i)\bis\s+not\b',  'is_not',  query )
    query = re.sub( r'(?i)\bbut\s+not\b', 'but_not', query )

    query = re.sub( r'(?i)\bexternally\b',     'external', query )
    query = re.sub( r'(?i)\b(opened|filed)\b', 'reported', query ) 

    query = re.sub( r'(?i)\bunprioritized\b', 'priority:0',            query )
    query = re.sub( r'(?i)\bunassigned\b',    'PrimaryDeveloper:none', query )

    query = re.sub( r'(?i)\bfunc(|tional)\s*category\b', r'FunctionalCategory', query )
    query = re.sub( r'(?i)\bfunc(|tional)\s*area\b',     r'FunctionalArea',     query )
    query = re.sub( r'(?i)\bfcat\b',  'FunctionalCategory', query )
    query = re.sub( r'(?i)\bfarea\b', 'FunctionalArea', query )

    query = re.sub( r'(?i)\b(reported\s*by|reporter|from)s?\b', 'ReportedBy',       query )
    query = re.sub( r'(?i)\b(primary\s?|)devel(|oper)s?\b',     'PrimaryDeveloper', query )
    query = re.sub( r'(?i)\bassigned\s+to\b',                   'PrimaryDeveloper', query )
    query = re.sub( r'(?i)\b(project\s?|)managers?\b',          'ProjectManager',   query )
    query = re.sub( r'(?i)\b(qa\s*contact|tester)s?\b',         'QAContact',        query )

    # -- take 'has' 'contain' to do a keyword search
    query = re.sub( r'(?i)\b(?:summary|subject|header|head)\s+(?:has|having|contains|containing)\s+(\S+)\b', r'summary:\1', query )
    query = re.sub( r'(?i)\b(problem|description|body)\s+(?:has|having|contains|containing)\s+(\S+)\b', r'\1:\2', query )

    # -- <person> as <role>, with no <role>
    query = re.sub( r'(?i)\b(\w+)\s+as\s+(ReportedBy|PrimaryDeveloper|ProjectManager|QAContact)s?\b', r'\2:\1', query )
    query = re.sub( r'(?i)\b(with\s+no|with\s*out(|\s+a))\s+(ReportedBy|PrimaryDeveloper|ProjectManager|QAContact)s?\b', r'\3:none', query )

    query = re.sub( r'(?i)\b(last\s*updated?)(\s+(in|on)|)\b', 'LastUpdate',    query )
    query = re.sub( r'(?i)\b(active|updated?)(\s+(in|on)|)\b', 'LastUpdate',    query )

    if re.search( r'(?i)\bfixed\b', query ):
       query = query.replace('fixed', 'resolved') + ' Resolution:Fixed' 

    query = re.sub( r'(?i)\bsee\s+also\s+tag\b', 'SeeAlso', query )
    query = re.sub( r'(?i)\btag(|ged)\b',        'SeeAlso', query )

    if not re.search( r'(?i)probability\s*and\s*statistics', query ):
        query = re.sub( r'(?i)\bstatistics\b', 'ProbabilityAndStatistics', query )

    # -- delete things that do not add anything to the query any more
    query = re.sub( r'(?i)\b(and|but)\s+still\b', '',  query ) 
    query = re.sub( r'(?i)\b(reports|a|as|the|that|those|whose|of|for|for\s+which|of\s+which|am|are|with|having)\b', '',  query ) 

    query = query.strip()

    return query


def translate_pattern( query ):
    """
    This is just like translate_basic(), but translates patterns that have to be avoidable with forced setting.
    e.g. if crm?\d+? => crm(\d+), it should be avoidable with e.g. SeeAlso:CRM[12345]
    """
    def make_related_report_see_also( m ):
        """
        conversion something like crm 123, 1233, ... SeeAlso:crm(123),crm(1233),
        """
        g = m.groups()
        rep_type_head, rep_nums_str = g[0], g[1] # -- e.g. "crm", "1223, 1234, and|or 1234"
        rep_nums_str = rep_nums_str.replace('and',' ').replace('or', ' ').replace(' ',  ',').strip(',')
        rep_nums_str = re.sub( r',+', ',', rep_nums_str )
        see_also_str = 'SeeAlso:' + rep_type_head + '(' + rep_nums_str.replace( ',', '),'+rep_type_head+'(' ) + ')' # -- e.g. SeeAlso:bug(12345),bug(54321)

        if rep_type_head.lower() == 'bug':    # -- yester year's SeeAlso bug references do not have bug() enclosure
            see_also_str += ','+rep_nums_str  # -- So, add just comma separated bug numbers too

        return see_also_str

    # -- find crm (can add more types in the paranthesis if needed) references to look in SeeAlso
    query = re.sub( r'(?i)(?:related\s+to\s+|)\b(crm)((\s*(\D?\d+\D?|,|and|or))*)\b',  lambda m: make_related_report_see_also( m ), query ) # find CRM references etc.

    # -- find bug (can add more types in the paranthesis if needed) references to look in SeeAlso
    # -- require 'related to' for bugs as the bug number in question will be loaded otherwise
    query = re.sub( r'(?i)related\s+to\s+(bug)((\s*(\D?\d+\D?|,|and|or))*)\b',  lambda m: make_related_report_see_also( m ), query ) # -- find bug references in SeeAlso

    query = re.sub( r'(?i)\b(version\s+|)V([\d\.]+)\b', r'version \2', query ) # -- version V10, V10 => version 10
    query = re.sub( r'(?i)\bM([\d\.]+)\b',  r'Mathematica version \1', query ) # -- M10 => Mathematica version 10
    query = re.sub( r'(?i)\b(Mathematica|WolframAlpha)\s*(\d+)(\s|$)',  r'\1 version \2\3', query ) # -- M10 => Mathematica version 10

    query = re.sub( r'(?i)\bplayer\s*pro\b',  r'MathematicaPlayerPro', query )
    query = re.sub( r'(?i)\bplayer\b',        r'MathematicaPlayer',    query )

    # -- ....in Mathematica version 10 => Mathematica ....in version 10  (makes parsing actions easier)
    query = re.sub( r'(?i)^(.*\sin\s+)(\S+\s+)(version.*)$', r'\2\1\3', query ) 

    return query


def separate_described_segments( query ):
    """
    Separate the decribed (e.g. Attr1:val1,val2) and so far non described (free words) query elements
    Returns two lists: decribed and nondescribed
    """
    query = re.sub( r',(\w+:)', r', \1', query.strip() ) 
    elems = shlex.split( query )

    decribed, nondescribed = [], []
    for e in elems:
        if ':' in  e: 
            e = e.strip(', ')
            attr, val = e.split(':')
            if ' ' in val: decribed.append( attr+':'+repr(val) )
            else         : decribed.append( e )
            nondescribed.append( HOLE ) # -- pasrsed out
        else:
            nondescribed.append( e )

    return decribed, nondescribed


def get_attr_vals_begin_with( dbc, word ):
    """
    helper function for contract_phrase(): returns the attribute values that begin with word
    """
    cur = dbc.cursor()
    query = "select value from attribute_value_index where value like '"+word+"%' and skip=0"
    cur.execute( query )

    values = []
    while True:
        row = cur.fetchone()
        if row is None: break
        values.append( row['value'] )

    cur.close()
    return values


def contract_phrase( dbc, words=[] ):
    """
    helper function for contract_parts():
    contracts a space separated query phrase or a list of words in such way to match 
    the maximum possible length. A list is preferred to avoid repeated string splitting 
    e.g. "primary developer jack import export bugs" => "primarydeveloper jack importexport bugs"
    """
    if not words: return None 

    if type(words) is str: # -- if a string given split into a list
        words = re.split( r'\s+', words )

    if re.match( r'^\d+$', words[0] ) or words[0].lower() in ('in','on'): # -- skip matching with the database
        word_contracted = words[0]
        words_rest      = words[1:]
    else:
        in_db = {}
        vals_begin_with_first_word = get_attr_vals_begin_with( dbc, words[0] )
        for val in vals_begin_with_first_word: in_db[ val.lower() ] = 1 # -- compare with lower case

        split_i = 1
        for i in reversed( range(0,len(words)) ):
            split_point = i + 1
            str_test = ''.join( words[:split_point] ).lower()
            if in_db.has_key( str_test ):
                split_i = split_point
                break

        word_contracted = ''.join( words[:split_i] )
        words_rest      = words[split_i:]

    if words_rest:
        return word_contracted + ' ' + contract_phrase( dbc, words_rest )
    else:
        return word_contracted


def contract_parts( dbc, query ):
    """
    Contracts a query string to match bugs db attribute values (e.g. 'import export' => 'importexport').
    Terms separated by '____' (HOLE), ':' and ',' are kept separate
    """
    parts_hole = []
    for e_hole in re.split( eval("r'\s*"+HOLE+"\s*'"), query ):
        parts_col = []
        for e_col in re.split( r'\s*:+\s*', e_hole ):
            parts_com = []
            for e_com in re.split( r'\s*,+\s*', e_col ):
                if e_com.strip() in (''): # -- anything that won't find any contraction
                    parts_com.append( e_com )
                else:
                    words = re.split( r'\s+', e_com )
                    phrase = contract_phrase( dbc, words )
                    parts_com.append( phrase )
    
            parts_col.append( ','.join( parts_com ) )
        parts_hole.append( ':'.join( parts_col ) )
    query_contr = eval("' '+HOLE+' '").join( parts_hole )

    return query_contr


def set_actor( oMatch, format_id ): # -- might become OBSOLETE
    """
    helper function for translate_action_in_version().
    This sets ReportedBy, ResolvedBy, or ResolveTestedBy when an action
    in version(s) are givin. e.g. iliang reported in 10.0.1
    """
    g = oMatch.groups()
    if format_id == 1: # -- rest: what's left after parsing out ActionBy:Person
        all, user, action, rest = g[0], g[1], g[3], g[2]
    elif format_id == 2:
        all, user, action, rest = g[0], g[2], g[1], g[1]+' '+g[3]+' '+g[4]
    elif format_id == 3:
        all, user, action, rest = g[0], g[4], g[1], g[1]+' '+g[2]+' '+g[3]
    else:
        raise "SetActorNoMatch"

    if personQ( user ):
        action_lower = action.lower()
        if action_lower == 'reported':
            return 'ReportedBy:'+user+' '+rest
        elif action_lower == 'resolved':
            return 'ResolvedBy:'+user+' '+rest
        elif action_lower == 'closed' or re.match(r'resolve\s*tested', action_lower):
            return 'ResolveTestedBy:'+user+' '+rest
        else:
            return all
    else:
        return all


def translate_action_in_version( query ): # - might become OBSOLETE
    """
    Called in the middle of translate_versions()
    Set ReportedBy, ResolvedBy, and ResolveTestedBy if a version specific action is given.
    By this stge the query must take the form "<action> <in|since|....> version \d[\d\.,]*"
    or similar (see translate_versions).
    """
    action_regexp = 'reported|resolved|closed|resolve\s*tested'
#   ver_op_regexp = 'in|before|after|till|until|since|from|inorbefore|inorafter|upto|upuntil'
    ver_op_regexp = 'in|before|after|till|until|since|from|(?:in|on)orbefore|(?:in|on)orafter|upto|upuntil|<|>|<=|>=|lt|gt|le|ge'
    # -- sometimes people use constructs such as resolved in <10.0.2

    # -- resolve V10.1 and 10.1 to "version 10.1"
    query = re.sub( eval("r'(?i)\\b("+ver_op_regexp+")\s+(?:version|V)\s*([\d\.,]+)'"), r'\1 version \2', query )
    query = re.sub( eval("r'(?i)\\b("+ver_op_regexp+")\s*(\d+\.[\d\.,]+)'"), r'\1 version \2', query )

    # <person> <action> <in|since|....> <version> ... sometimes people try "resolve in <10.0.1", hence (?:\s+in)?
    query = re.sub( eval("r'(?i)\\b(([a-z]+)\s+(("+action_regexp+")(?:\s+in)?\s+("+ver_op_regexp+")(?:\s+version\s+\d[\d\.,]*|\s*\d+\.[\d\.,]*)))'"), lambda m: set_actor(m,1), query )

    # <action> by <person> <in|since|....> <version>
    query = re.sub( eval("r'(?i)\\b(("+action_regexp+")\s*by\s+([a-z]+)(?:\s+in)?\s+("+ver_op_regexp+")(\s+version\s+\d[\d\.,]*|\s*\d+\.[\d\.,]*))'"), lambda m: set_actor(m,2), query )

    # <action> <in|since|....> <version> by <person>
    query = re.sub( eval("r'(?i)\\b(("+action_regexp+")(?:\s+in)?\s+("+ver_op_regexp+")(\s+version\s+\d[\d\.,]*|\s*\d+\.[\d\.,]*)\s+by\s+([a-z]+))'"), lambda m: set_actor(m,3), query )

    return query


def translate_versions( query ):
    """
    translate version specifications. If just the string 'version' is given. ResolutionVersion is assumed when feature
    reports seem to be saught; otherwise, VersionReported
    Update: does only very basic transformations... action parsing handles most
    """
    # -- e.g. 10.1.x => 10.1
    query = re.sub( r'(?i)\b(version\s*(reported|resolved|))(\s*\d+(\.\d+)*)\.(x\.)*x\b', r'\1\3', query ) # -- version [reported] 10.x
    query = re.sub( r'(?i)\b(\d+(\.\d+)*)\.(x\.)*x\b', r'version \1', query ) # -- 10.x (this should come after the above)

    # -- contract 'up until', 'in or after', etc..
### DEVEL
#   query = re.sub( r'(?i)\b(?:in|on)\s*or\s*(before|after)(\s*(version|V|\d+\.))', r'inor\1\2', query )
#   query = re.sub( r'(?i)\bup\s*(to|until)(\s*(version|V|\d+\.))', r'up\1\2', query )

#   query = translate_action_in_version( query )

    # DEVEL -- translate_action_in_version() (later added) converts "10.1" and V10.1 to "version 10.1"
    #       -- Following patterns maybe simplyfied once confident about translate_action_in_version()

    # -- 'closed', 'resolved tested' => 'resolved' if what follows is a version (there's no closed or resolve tested version attr)
#   ineq_op_regexp_1 = 'before|after|till|until|since|from|(?:in|on)orbefore|(?:in|on)orafter|upto|upuntil|<|>|<=|>=|lt|gt|le|ge'
#   query = re.sub( eval("r'(?i)\\b(?:closed|resolve\s+tested)\s+(in|"+ineq_op_regexp_1+")\s*(?:version|V)\s*([\d\.,]*)'"), r'resolved \1 version \2', query )
#   query = re.sub( eval("r'(?i)\\b(?:closed|resolve\s+tested)\s+(in|"+ineq_op_regexp_1+")\s*(\d+\.[\d\.,]+)'"), r'resolved \1 version \2', query )

    # -- reported in
#   query = re.sub( eval("r'(?i)\\breported\s+in\s+(|version\s*|V?)([\d\.,]+)'"), r'VersionReported:\2',   query )
#   query = re.sub( eval("r'(?i)\\bresolved\s+in\s+(|version\s*|V?)([\d\.,]+)'"), r'ResolutionVersion:\2', query )

    # -- reported before|after... 10.*|V10|version 10... and the odd "reported in <10.10" and hence (?:\s+in)?
#   query = re.sub( eval("r'(?i)\\breported(?:\s+in)?\s+("+ineq_op_regexp_1+")\s*(\d+\.[\d\.]*)'"), r'VersionReported:\1\2',   query )
#   query = re.sub( eval("r'(?i)\\bresolved(?:\s+in)?\s+("+ineq_op_regexp_1+")\s*(\d+\.[\d\.]*)'"), r'ResolutionVersion:\1\2', query )
#   query = re.sub( eval("r'(?i)\\breported(?:\s+in)?\s+("+ineq_op_regexp_1+")\s*(version|V)\s*([\d\.]+)'"), r'VersionReported:\1\3',   query )
#   query = re.sub( eval("r'(?i)\\bresolved(?:\s+in)?\s+("+ineq_op_regexp_1+")\s*(version|V)\s*([\d\.]+)'"), r'ResolutionVersion:\1\3', query )
 
    # -- version reported == V10, etc.
    math_eq_op_regexp = '=|==|eq'
    query = re.sub( eval("r'(?i)\\b(version|versionreported|resolutionversion)\s*(?:|"+math_eq_op_regexp+")\s*V?([\d\.]+)'"), r'\1 \2', query )

    # -- version reported < V10, etc.
    math_ineq_op_regexp   = '<|lt|<=|le|>|gt|>=|ge'
    query = re.sub( eval("r'(?i)\\b(version|versionreported|resolutionversion)\s*("+math_ineq_op_regexp+")\s*V?([\d\.]+)'"), r'\1 \2\3', query )

    # -- V10 (still left for whatever reason)
#   query = re.sub( r'\bV([\d\.]+)', r'version \1', query )

# DEVEL -- take in further down
#   versionM = re.compile( eval("r'(?i)\\bversion\s+(|"+math_ineq_op_regexp+")([\d\.,]+)'") )
#   if re.search( versionM, query ):
#       if featuresQ:
#           query = re.sub( versionM, r'ResolutionVersion:\1\2', query )
#       else:
#           query = re.sub( versionM, r'VersionReported:\1\2', query )

    return query


def fill_value_attr_dic( dbc, query ):
    """
    given a query phrase, this returns { 'value1':'attr1', 'value2':'attr2', ...}
    The input should have only non described segments. i.e. not segments like priority:1,2 or ReportType:Crash,Hang
    but only single words and comma separated lists. e.g. 'Open', 'Open,Resolved'
    """
    if query is None or not query.strip(): return {}
    query = query.strip()

    query_elems_ss, spaceM, dateM = re.split( r'\s+', query ), re.compile(r'\s'), re.compile(r'(today|yesterday|\d{8}|day|week|month|year)')
    for elem in query_elems_ss: # -- some rough checks
        if not spaceM.search(elem) and dateM.search(elem): VALUE_INDEX[elem] = 'date'

    query_elems_sc = re.split( r'[\!\s,]+', query )
    to_ignore   = (HOLE,'is','in','on','and','or','for','not','but','tag','with','today','yesterday','version','before','after') 
    vals_to_find = filter( lambda x: not( x.isdigit() or x in to_ignore ), query_elems_sc )
    vals_str     = ','.join(vals_to_find).replace( ',', "','" ) # - some itmes are comma separated lists
    
    cur = dbc.cursor()
    q_db = "select lower(value) as value,attribute from attribute_value_index where value in ('"+vals_str+"') and skip=0 order by value,score_override,score"

    cur.execute( q_db )

    attr_names_lower, val_attr_dict = ATTRIBUTES.keys(), {}
    while True: # -- get values likely find in the db table
        row = cur.fetchone()
        if row is None: break

        if row['value'] in attr_names_lower: # -- force attribute names
            val_attr_dict[ row['value'] ] = 'attribute'
        elif row['attribute'].lower() in ('reportedby','resolvedby','resolvetestedby'): # -- assign more important role (PD, PM, QAC) if exists
                role = Bugs.GetRole( row['value'], dbc )
                if role: val_attr_dict[ row['value'] ] = role
                else:    val_attr_dict[ row['value'] ] = row['attribute']
        else:
            val_attr_dict[ row['value'] ] =  row['attribute']

    cur.close()

    date_op_regexp  = '>|>=|<|<=|lt|le|gt|ge|before|after|from|since|between|on|onorbefore|onorafter'
    day_name_regexp = 'sunday|monday|tuesday|wednesday|thursday|friday|saturday|today|yesterday'
    dateM1 = re.compile( eval("r'(?i)^(|"+date_op_regexp+")(last|)("+day_name_regexp+"|\d{8})'") )
    dateM2 = re.compile( r'(?i)^(this|last)\d*(day|week|month|year)' )

    ver_op_regexp = '=|==|eq|<|lt|<=|le|>|gt|>=|ge|before|after|till|until|since|from|(?:in|on)orbefore|inorafter|upto|upuntil'
    verM1 = re.compile( eval("r'(?i)^("+ver_op_regexp+")[\d\.,]+'") )
    verM2 = re.compile( r'\d+\.[\d\.,]+' )

    running_attr, priM = None, re.compile( r'(?i)^priority$' )
    for elem in query_elems_sc: # -- go through all elements in the query phrase
        if elem == HOLE: continue
        elem = elem.lower()

        if re.match( r'(?i)^(none|unknown|unassigned|undef|missing|undefined|unclassified)$', elem ): 
            VALUE_INDEX[elem] = 'univ_value'
            continue

        try:
            attr_db = val_attr_dict[elem]
            VALUE_INDEX[elem] = val_attr_dict[elem]

            if attr_db == 'attribute': 
                running_attr = elem
            else:
                running_attr = val_attr_dict[elem]
        except KeyError:
            if dateM1.match( elem ) or dateM2.match( elem ): 
                VALUE_INDEX[elem] = 'date'
            elif elem in ('0','1','2','3','4','5') and running_attr and priM.match( running_attr ):
                VALUE_INDEX[elem] = running_attr
            elif verM1.match( elem ) or verM2.match( elem ):
                VALUE_INDEX[elem] = 'version'
            else:
                VALUE_INDEX[elem] = None

    # -- hard coded value identification
    for attr, vals in KNOWN_IDS.items():
        for val in vals:
            val_lower = val.lower()
            VALUE_INDEX[val_lower] = attr
            val_attr_dict[val_lower] = attr

    # -- duplicate values such as '<yesterday' with 'yesterday' for flexibility
    for key,val in VALUE_INDEX.items():
        key_dup = key.strip("<=>!")
        if key_dup != key: VALUE_INDEX[key_dup] = val

    return val_attr_dict


def get_possible_usenames( dbc, name ):
    """
    Here 'name' could be some name: first, last, or middle..
    This returns a list of possible user/login names.
    """
    cur_user = dbc.cursor()
    q_user = 'select name from user where realname rlike "[[:<:]]'+name+'[[:>:]]"'
    cur_user.execute( q_user )

    if cur_user.rowcount < 1: 
        cur_user.close()
        return []

    unames = []
    while True:
        row = cur_user.fetchone()
        if row is None: break
        unames.append( row['name'] )
    cur_user.close()

    return unames


def translate_names( dbc, query ):
    """
    If a word has not been identified yet and has the potential to be some name
    (first, last, etc.), but not the login name, try to figure that out
    """
    # -- chars expected/allowed in username, any alphabetic char
    un_charM, alphaM = re.compile( r'^[\d\w\.\-]+$' ), re.compile( r'[a-zA-Z]' )

    cur, map = dbc.cursor(), {}
    to_ignore   = (HOLE,'is','are','in','on','where','those','that','and','or','for','not','but','by','tag','with','today','yesterday','version') 
    for key, val in VALUE_INDEX.iteritems(): # -- note here dict key is actually attr val, and dict val is attr or None
        if val is not None or key in to_ignore or not alphaM.search(key) or not un_charM.match(key): continue

        usernames = get_possible_usenames( dbc, key )

        # -- score threshold is meant for cut off noise such as 'arnoud', 'shiral', etc.
        q_db  =  "select    lower(value) as value, attribute from attribute_value_index"
        q_db += " where     value in ('" + "','".join( usernames ) + "') and skip=0 and score > 1000"
        q_db += " order by  score_override desc, score desc limit 1"

        cur.execute( q_db )
        row = cur.fetchone()
        try   : map[key] = { 'username':row['value'], 'attribute':row['attribute'] }
        except: pass

    for query_word, map_dict in map.iteritems(): 
        query = re.sub( eval("r'(?i)\\b"+query_word+"\\b'"), map_dict['username'], query )
        VALUE_INDEX[ map_dict['username'] ] = map_dict['attribute']

    return query


def resolve_action( oMatch, format_id ):
    """
    helper function for translate_action() to translate actions (report, resolve, resolve test)
    when the person and the date is specified in the same phrase
   
    Update: besides format_id=6, every other case is likely to become OBSOLETE
    """
    attr_name = { 'reported':['ReportedBy','DateReported'], 'resolved':['ResolvedBy','DateResolved'], 'resolvetested':['ResolveTestedBy','DateResolveTested'], 'closed':['ResolveTestedBy','DateResolveTested'], 'lastupdate':['','LastUpdate'] }

    g = oMatch.groups()
    try:
        # -- <date> has 2 captured patterns
        if   format_id == 1 and personQ(g[2]) and VALUE_INDEX[g[5]] == 'date': # -- <action>, by, <person>, [on], <date>
            action = g[0].lower().replace(' ','')
            return attr_name[action][0]+':'+g[2]+' '+attr_name[action][1]+':'+g[5]
        elif format_id == 2 and personQ(g[6]) and VALUE_INDEX[g[3]] == 'date': # -- <action>, [on], <date>, by, <person>
            action = g[0].lower().replace(' ','')
            return attr_name[action][0]+':'+g[6]+' '+attr_name[action][1]+':'+g[3]
        elif format_id == 3 and personQ(g[0]) and VALUE_INDEX[g[4]] == 'date': # -- <person> <action> [on] <date>
            action = g[1].lower().replace(' ','')
            return attr_name[action][0]+':'+g[0]+' '+attr_name[action][1]+':'+g[4]
        elif format_id == 4 and personQ(g[0]): # -- <person> <action>
            action = g[1].lower().replace(' ','')
            return attr_name[action][0]+':'+g[0]
        elif format_id == 5 and VALUE_INDEX[g[3]] == 'date': # -- <action>, [on], <date>
            action = g[0].lower().replace(' ','')
            return attr_name[action][1]+':'+g[3]
        elif format_id == 6 and VALUE_INDEX[g[5]] == 'date': # -- <action>, [on], <date>
            action_pos = g[0].lower().replace(' ','')
            action_neg = g[2].lower().replace(' ','')
            date_spec  = g[5]
            return attr_name[action_pos][1]+':'+date_spec+' '+attr_name[action_neg][1]+':!'+date_spec
        else:
            raise "NoMatch"
    except:
        raise "NoMatch"


def translate_action_pre( query ):
    """
    Specifically traslate one-off actions such as "updated but not reported today".
    Such constructs are not generally transformed as it gets complicated when
    multiple actions and negations get involved.
    """

    # -- these patterns may cover more than what makes sense, but such nonsensical queries are unlikely
    event_spec  = '(reported|resolved|resolve\s*tested|closed|last\s*updated?)'
    action_spec = '(reported|resolved|resolve\s*tested|closed)'
    period_prep = '(\s+(on|in|during|within)\s+|\s+)'
    period_spec = '(\S*(today|yesterday|\d{8}|day|week|month|year)\S*)'

    # -- e.g. updated but not reported today
    reg_exp6 = re.compile( eval( "r'(?i)\\b" + event_spec + "\s+(but[\s_]not|not)\s+" + event_spec + period_prep + period_spec + "'" ) )
    try: query = re.sub( reg_exp6, lambda m: resolve_action(m,6), query )
    except: pass

    return query


def translate_action_OLD( query ):
    """
    attempt to translate reported, resolved, closed etc. when both the person and the date
    is specified in one phrase (e.g. resolved by carlosy yesterday) 
    Dates should come parsed by this stage. 
    """

    # -- these patterns may cover more than what makes sense, but such nonsensical queries are unlikely
    event_spec  = '(reported|resolved|resolve\s*tested|closed|last\s*updated?)'
    action_spec = '(reported|resolved|resolve\s*tested|closed)'
    period_prep = '(\s+(on|in|during|within)\s+|\s+)'
    period_spec = '(\S*(today|yesterday|\d{8}|day|week|month|year)\S*)'

    # -- e.g. updated but not reported today
    reg_exp6 = re.compile( eval( "r'(?i)\\b" + event_spec + "\s+(but[\s_]not|not)\s+" + event_spec + period_prep + period_spec + "'" ) )
    try: query = re.sub( reg_exp6, lambda m: resolve_action(m,6), query )
    except: pass

    # -- <action> by <person> [on] <date>
    reg_exp1 = re.compile( eval( "r'(?i)\\b" + action_spec + "\s*(by)\s+([a-z]+)" + period_prep + period_spec + "'") )
    try:    query = re.sub( reg_exp1, lambda m: resolve_action(m,1), query )
    except: pass

    # -- <action> [on] <date> by <person>
    reg_exp2 = re.compile( eval("r'(?i)\\b" + action_spec + period_prep + period_spec + "\s+(by)\s+([a-z]+)'") )
    try:    query = re.sub( reg_exp2, lambda m: resolve_action(m,2), query )
    except: pass

    # -- <person> <action> [on] <date> (bit risky as this could pull a person meant for another attribute)
    reg_exp3 = re.compile( eval("r'(?i)\\b([a-z]+)\s+" + action_spec + period_prep + period_spec + "'") )
    try:    query = re.sub( reg_exp3, lambda m: resolve_action(m,3), query )
    except: pass

    # -- <person> <reported|resolve tested> -- exclude 'resolved' and 'closed' as they also are Status values
    reg_exp4_1 = re.compile( r'(?i)\b([a-z]+)\s+(reported|resolve\s*tested)\b' )
    try:    query = re.sub( reg_exp4_1, lambda m: resolve_action(m,4), query )
    except: pass

    # -- bugs [that] <person> <resolved|closed>
    if re.search( r'(bugs|features|suggestions|reports)\s+(|that\s+|which\s+)([a-z]+)\s+(resolved|closed)', QUERY ):
        reg_exp4_2 = re.compile( r'(?i)\b([a-z]+)\s+(resolved|closed)\b' )
        try:    query = re.sub( reg_exp4_2, lambda m: resolve_action(m,4), query )
        except: pass

    # -- <action> [on] <date>
    reg_exp5 = re.compile( eval("r'(?i)\\b" + action_spec + period_prep + period_spec + "\\b'") )
    try:    query = re.sub( reg_exp5, lambda m: resolve_action(m,5), query )
    except: pass

    return query


def get_attr_type( elem ):
    """
    helper function for parse_action_segment(). It returns the attribute type in an
    action segment such as "resolved by danl in version 10.0.0 last 2 weeks" (after
    contraction and some processing) hinting which way the term should go. It detects
    only the three type that could be in such segments (person, version, data, or None).
    """
    elem = elem.lower()

    if personQ( elem ): 
        attr_type = 'person'
    elif re.search( r'(?i)(day|week|month|year|\d{8})', elem ):
        attr_type = 'date'
    elif re.search( r'(?i)(version|V[\d\.]+|\d\.[\d\.]*)', elem ):
        attr_type = 'version'
    else:
        attr_type = None

    return attr_type

def get_next_attr_type( elem ):
    """
    helper function for parse_action_segment(). Given a preposition it tries to
    hint what kind of attribute is following in an action segment such as "resolved 
    by danl in version 10.0.0 last 2 weeks" (after contraction and some processing).
    The scope is limited to the types 'person', 'date', and 'version' (potentially)
    """
    elem = elem.lower()

    if elem == 'by': 
        next_attr_type = 'person'
    elif elem in ('within','during'):
        next_attr_type = 'date'
    elif elem == 'version':
        next_attr_type = 'version'
    else:
        next_attr_type = None

    return next_attr_type


def parse_action_segment( segment, followed_by ):
    """
    Parses action segments such as "resolved by danl in version 10.0.1 last 3 weeks".
    The argument 'segment' is an array of tokens of an action segment.
    """
    if len(segment) < 2: # -- set a threshold to the segment
        return ' '.join( segment )

    # -- skip the cases where 'resolved' and 'closed' and most probably status values 
    # -- e.g. "carlosy resolved bugs"
    conjuncs = 'by|in|within|during|on|before|after|up|until|up|since|from|<|>|lt|gt|le|ge|today|yesterday|last|\d{8}|whose|'+HOLE
    action_conjQ = followed_by and re.match( eval("r'(?i)("+conjuncs+")'"), followed_by )
    if segment[-1].lower() in ('resolved','closed') and followed_by and not action_conjQ:
        return ' '.join( segment )

    if segment[-1].lower() in ('and'): segment.pop() # -- trailing words to ignore

    attrs   = {     'reported':{'date':'DateReported',      'version':'VersionReported',   'person':'ReportedBy'}, \
                    'resolved':{'date':'DateResolved',      'version':'ResolutionVersion', 'person':'ResolvedBy'},\
               'resolvetested':{'date':'DateResolveTested', 'version':'ResolutionVersion', 'person':'ResolveTestedBy'}}
    actions = attrs.keys()

#   if segment[0].lower() in actions:   # -- "resolved by..." or "reolved in....", etc.
#       action, segment[0] = segment[0].lower(), segment[0].lower()
#   elif segment[1].lower() in actions and personQ(segment[0]): # -- <person> resolved ... => resolved by <person>
#       action, segment[1], segment[0] = segment[1].lower(), segment[0], segment[1].lower()
#       segment.insert( 1, 'by' )


    action = segment.pop(0).lower() # -- action token

    next_attr_type, running_attr_type, running_attr, prep, parsed, negateQ = None, None, None, [], {}, False
    for elem in segment:
        elem_lower = elem.lower()

        if not negateQ and elem_lower in ( 'not', 'but_not' ) and running_attr not in parsed: 
            negateQ = True
            continue

        # -- try to detect the attr of the current element and set it as the running attr
        if next_attr_type:
            running_attr_type, running_attr, next_attr_type = next_attr_type, attrs[action][next_attr_type], None
        else:
            elem_attr_type = get_attr_type( elem_lower )
            if elem_attr_type: 
                running_attr_type, running_attr = elem_attr_type, attrs[action][elem_attr_type]
   
        # -- try to detect the  next attribute (e.g. after 'by')
        next_attr_type = get_next_attr_type( elem_lower )

        # -- detect prepositions
        if elem_lower in ('by','within','during','version'): # -- those that can safely ignore
            continue
        elif elem_lower in ('in','on','or','before','after','upto','up','to','till','until','since','from','<','>','<=','>=','lt','gt','le','ge'): # -- prepositions saved for the next
            prep.append( elem )
            continue

        if prep: # -- if there are preposition, put them in
            try            : parsed[running_attr].extend(prep)
            except KeyError: 
                if negateQ: 
                    prep.insert(0, '!')
                    negateQ = False
                parsed[running_attr] = prep[:]
            prep = []

        # -- attribute type specific translations
        if running_attr_type == 'person':
            if   elem_lower == 'and'     : elem = '+'
            elif elem_lower == 'or'      : elem = ','
            elif elem_lower == 'but_not' : elem = '-'

        try            : parsed[running_attr].append(elem)
        except KeyError: 
            if negateQ: 
                parsed[running_attr] = ['!'+elem]
                negateQ = False
            else:
                parsed[running_attr] = [elem]

    parsed_elems = [] # -- join the resolved attr and vals 
    for attr, tokens in parsed.iteritems():
        val = ''.join(tokens)
        val = re.sub( r'^(?:in|on)([\d><])', r'\1', val ) # -- e.g. in10.0.1 => 10.0.1 
        parsed_elems.append( attr+':'+val )


    parsed_str = ' '.join( parsed_elems )
    return parsed_str


def fix_action( m ):
    """
    helper function for translate_action(). This fixes segments such as "rbergman closed in ..."
    to "rbergman resolvetested in ...". Whether "closed" is a status or an action depends on the
    context
    """
    if personQ( m.group(1) ): # -- e.g. "rbergman closed in ...." then closed => resolvetested
        person, action, conj = m.group(1), 'resolvetested', m.group(3)
        new_str = person + ' ' + action + ' ' + conj
        return new_str
    else:
        return m.group(0)


def analyze_not( query ):
    """
    This replaces or rearranges 'not' and 'but_not' to prepare the query for further processing.
    If came between two persons, it's replaced with '-'
    If came in front of an action (reported, resolved, or resolvetested), it's pushed behind it.
    By this stage, the action words should come properly translated to either
    reported, resolved, or resolvetested
    """
    tokens = query.split()

    conjuncs = ('by','in','within','during','before','after','on','up','until','up','since','from','between',\
                '<','>','lt','gt','le','ge','today','yesterday','last','\d{8}')
    conjunc_pat = '|'.join( conjuncs )
    conjM = re.compile( eval("r'("+conjunc_pat+")'") )

    n = len(tokens)
    prev_to_prev, prev, next, next_to_next = None, None, None, None
    for i in range(n):
        try              : next = tokens[i+1]
        except IndexError: next = None
        try              : next_to_next = tokens[i+2]
        except IndexError: next_to_next = None

        tok_lower = tokens[i].lower()
        if tok_lower in ('not', 'but_not'):
            if personQ(prev) and personQ(next):
                tokens[i] = '--minus--'
            elif next in ('reported', 'resolvetested') or (next == 'resolved' and conjM.match(next_to_next)):
                tokens[i], tokens[i+1] = next, 'not'

        if prev != None: 
            prev_to_prev = prev
        prev = tokens[i]

    query = ' '.join(tokens)

    return query


def translate_action( query ):
    """
    parses action segments such as "resolved by rknapp in 10.0.2 last week".
    Later, translate_version and translate_action should be reviewed and 
    merge with this.
    """
    query = re.sub( r'(?i)\bV([\d\.]+)', r'version \1', query )

    query = re.sub( r'(?i)resolve\s*tested', r'resolvetested',    query )
#   query = re.sub( r'(?i)closed\s+by',      r'resolvetested by', query )
    # -- DEVEL e.g. "closed in verion 10 by"; see how this goes. closed\s+by (above) can be deleted if this words
    # --       Perhaps these two (above and below) not needed with the following with conjunc_pat
#   query = re.sub( r'(?i)closed\s+((?:\S+\s+){0,5}by)', r'resolvetested \1', query ) 
    query = re.sub( r'(?i)(reported|resolved|resolvetested)by', r'\1 by', query ) # -- resolvedby => resolved by

    conjuncs = ('by','in','within','during','before','after','on','up','until','up','since','from','between',\
                '<','>','lt','gt','le','ge','today','yesterday','last','\d{8}','whose')
    conjunc_pat = '|'.join( conjuncs )
    query = re.sub( eval("r'(?i)\\bclosed\s+("+conjunc_pat+")'"),      r'resolvetested \1', query ) # -- e.g. closed by|in|..
    query = re.sub( eval("r'(?i)(\w+)\s+(closed)\s+("+conjunc_pat+")'"), lambda m: fix_action(m), query ) # -- e.g. "<person> closed in" => "<person> resolvetested in"

    query = analyze_not( query )

    attr_lower       = ATTRIBUTES.keys()
    segment_attrs    = ('date','datereported','dateresolved','dateresolvetested','version','versionreported','resolutionversion',\
                     'person','reportedby','qacontact','primarydeveloper','productmanager','resolvedby','resolvetestedby')
    other_attr_lower = tuple(set(attr_lower) - set(segment_attrs))

    # -- by this stage all action alias must have been resolved
    actions = ('reported', 'resolved', 'resolvetested')
    elems, segment, rest, prev, collect = query.split(), [], [], '', False
    for e in elems:
        e_lower = e.lower()
        if collect:
            # -- breaks at discontinuity, another attribute, or a value belonging to another attribute
            other_attr_value = (e_lower in VALUE_INDEX and VALUE_INDEX[e_lower] != None and VALUE_INDEX[e_lower].lower() in other_attr_lower)
            if e in (HOLE) or e_lower in actions or e_lower in other_attr_lower or (other_attr_value and e not in conjuncs):
                segment_parsed_str, segment = parse_action_segment( segment, e ), []
                rest.append( segment_parsed_str )
                if e_lower in actions:
                    segment = [e]
                else:
                    rest.append( e )
                    collect = False
            else:
                segment.append( e )
        else: 
            if e_lower in actions:
                collect = True
                segment.append( e )
                if personQ(prev): # -- e.g. "danl resolved"; pull back and rearrage as "resolved by danl"
                    segment.extend( ['by',rest.pop()] )
            else:
                rest.append(e)

        prev = e

    if collect: # -- query ended while still building the segment 
        segment_parsed_str = parse_action_segment( segment, None )
        rest.append( segment_parsed_str )

    query_parsed = ' '.join( rest )

    return query_parsed


def translate_version_remains( query, featuresQ ):
    """
    try this if nothing -- mostly the action parsing -- succeeded in figuring out the version specification
    """
    math_ineq_op_regexp   = '<|lt|<=|le|>|gt|>=|ge'
    versionM = re.compile( eval("r'(?i)\\b(?:(?:in|on|for)\s+)?version\s+(|"+math_ineq_op_regexp+")([\d\.,]+)'") )
    if re.search( versionM, query ):
        if featuresQ:
            query = re.sub( versionM, r'ResolutionVersion:\1\2', query )
        else:
            query = re.sub( versionM, r'VersionReported:\1\2', query )

    return query


def relate( query ):
    """
    some attempt to relate 'is', 'is not', 'and', etc... but this is not reliable 
    and should be avoided in queries. They are better given specifically
    e.q. QAContact:shirald - carlosy rather that "qa contact is shirald but not carlosy"
    """
    elems = re.split( r'\s+', query )
    list_length = len( elems )

    for i in range( len(elems) ):
        if i: prev_elem_lower = elems[i-1].lower()
        else: prev_elem_lower = ''

        if i == (list_length - 1): next_elem_lower = ''
        else                     : next_elem_lower = elems[i+1].lower() 

        if prev_elem_lower == HOLE and next_elem_lower == HOLE: # -- sandwiched between two discontinuities
            if elems[i].lower() in ('and','or'): elems[i], elems[i+1] = '', '' 

        if ATTRIBUTES.has_key(prev_elem_lower): # -- following an attribute
            if   elems[i] in ('is','='):
                elems[i] = ':'
            elif elems[i] in ('is_not','not','!=','=!'):
                elems[i] = ':!'

        if ATTRIBUTES.has_key(next_elem_lower): # -- in front of an attribute
            if elems[i].lower() in ('and','or'): elems[i] = ''

        try: # -- resolved [as] AsDesigned => Resolution AsDesigned
            if elems[i].lower() == 'resolved' and VALUE_INDEX[next_elem_lower].lower() == 'resolution': 
                elems[i], VALUE_INDEX['resolution'] = 'Resolution', 'attribute'
        except:
            pass

        # -- top block is relevant to multi value attributes, but currently not every attribute 
        # -- in the database, e.g. Component, is perceived as multi value
        # -- Add FunctionalArea should need arise
        if personQ( prev_elem_lower ) and personQ( next_elem_lower ): # -- combining person (or multi-value attr values)
            if   elems[i] == 'and'    : elems[i] = '+' # -- shirald and carlosy etc..
            elif elems[i] == 'or'     : elems[i] = ',' 
            elif elems[i] == 'but_not': elems[i] = '-'
            elif elems[i] == 'not'    : elems[i] = '-'
        else:
            if   elems[i] == 'and'    : elems[i] = ',' # -- priority 1 and 2 etc.
            elif elems[i] == 'or'     : elems[i] = ','

    query_rel = ' '.join(elems)
    query_rel = re.sub( r'\s*(:!?)\s*',  r'\1', query_rel )
    query_rel = re.sub( r'\s*([,+])\s*', r'\1', query_rel )
    query_rel = re.sub( r',([+\-])',     r'\1', query_rel )

    return query_rel


def personQ( str ):
    """
    given a string checks if it's a person (reporter, developer, tester, manager, reported, etc..)
    VALUE_INDEX dictionary should be ready before calling this function
    """
    try:
        if VALUE_INDEX[str].lower() in ('primarydeveloper','projectmanager','qacontact','reportedby','resolvedby','resolvetestedby'):
            return True
        else: 
            return False
    except:
        return False


def expand_list( list_str ):
    """
    expand a list that may be separated by ',', '+', '---minus--', etc. into
    single elements. This has only a few lines, but needed more than once
    """
    list_str = re.sub( r'[+!~<=>]+', ',', list_str ).replace('--minus--',',')
    list_str = list_str.strip(' ,')
    list     = re.split( r'[\s,]+', list_str )

    return list

def check_attribute_single( val, attr ):
    """
    check if a single value attribute mataches the attribute specified. e.g. A person identified 
    as a tester would match a developer as they are both persons, or >10 would match a version.
    """
    person_attr_list  = ('primarydeveloper','projectmanager','qacontact','reportedby','resolvedby','resolvetestedby')
    date_attr_list    = ('datereported', 'dateresolved', 'dateresolvetested', 'dateclosed', 'lastupdate' )
    version_attr_list = ('versionreported', 'resolutionversion' )

    attr_ref_lower = attr.lower()

    if attr_ref_lower in date_attr_list: # -- basic date check
        if re.match( r'^[<=>\d,]+$', val ): return []

    if attr_ref_lower in version_attr_list: # -- basic version check
        if re.match( r'^[<=>\d\.,]+$', val ): return []

    # -- do simple pattern checks before checking in VALUE_INDEX 
    attr_ind_lower = VALUE_INDEX[ val.lower() ].lower()
    
    if ( attr_ind_lower == attr_ref_lower ): return []
    if ( attr_ind_lower in person_attr_list and attr_ref_lower in person_attr_list  ): return []
    if ( attr_ind_lower == 'date'           and attr_ref_lower in date_attr_list    ): return []
    if ( attr_ind_lower == 'version'        and attr_ref_lower in version_attr_list ): return []

    raise AttributeError


def check_attribute( list_str, attr ):
    """
    does a rouch check of items in comma (maybe more) separated list against a given attribute.
    Rough in the sense e.g. QAContact and PrimaryDeveloper matches as they are both persons.
    Returns a list of items that do not match the attribute.
    """
    try: # -- assume a single value (works in most cases)
        return check_attribute_single( list_str, attr )
    except (KeyError, AttributeError):
        pass

    # -- if cannot be found, try as a list
    list = expand_list( list_str )

    failures = []
    for item in list:
        if item == HOLE: continue

        try: # -- assume a single value
            check_attribute_single( item, attr )
        except (KeyError, AttributeError):
            failures.append( item )

    return failures


def run_through_rest( query, featuresQ ):
    """
    run through what's remaining of the query and try to relate.
    returns an two lists: resolved list [attr:vals, attr2:vals,...] and non_resolved words
    """
    if query is None or query.strip() == "": return [], []

    query = re.sub( r'\s*([,\s\+])[,\s\+]*', r'\1', query.strip() ) # -- separate by only one ',', '+', or a space

    elems_ss = re.split( r'\s+', query )

#   running_attr, resolve_dict, listM, failures = '', {}, re.compile( r'(,|\+|!|~|--minus--)' ), []
    running_attr, resolve_dict, listM, failures = '', {}, re.compile( r'(,|\+|!|~|--minus--)\S' ), []
    for e_ss in elems_ss:
        if e_ss.strip() in (''): continue # -- anything to skip

        if e_ss == HOLE: # -- terms parsed out; in other words, some kind of discontinuity
            running_attr = ''
            continue

        if running_attr: # -- if running attr known, check for a quick match
            try:
                fails = check_attribute( e_ss, running_attr )
                if not fails: 
                    resolve_dict[running_attr].append( e_ss )
                    continue
            except:
                pass

        val_ind_key = e_ss.strip('!<=>').lower()
        try: # -- identified single words
            if VALUE_INDEX[val_ind_key] == 'attribute': 
                running_attr = e_ss 
                if not resolve_dict.has_key(running_attr): 
                    resolve_dict[running_attr] = []
            elif VALUE_INDEX[val_ind_key] == 'univ_value': 
                resolve_dict[running_attr].append( e_ss )
            else:
                fails = check_attribute( e_ss, running_attr ) # -- see if matches with the running attr
                if fails: # -- not matched with running attribute
                    if VALUE_INDEX[val_ind_key] and VALUE_INDEX[val_ind_key] != 'None': # -- identified as another attribute
                        try:
                            resolve_dict[VALUE_INDEX[val_ind_key]].append( e_ss )
                        except KeyError:
                            resolve_dict[VALUE_INDEX[val_ind_key]] = [ e_ss ]
                    else: # -- not identified anyway
                        failures.append( e_ss )
                else: # -- matched with running attr
                    resolve_dict[running_attr].append( e_ss )
        except KeyError: # -- unidentified or list of values
            if re.search( listM, e_ss ): # -- list of values
                if running_attr is None or running_attr == '': # -- if running attr is not known try to figure out
                    list_elems = expand_list( e_ss )
                    if VALUE_INDEX.has_key(list_elems[0].lower()): 
                        running_attr = VALUE_INDEX[list_elems[0].lower()]
                        resolve_dict[running_attr] = []

                fails = check_attribute( e_ss, running_attr )
                if fails: failures += fails 

                if running_attr: # -- take them anyway, but log if failed, 
                    resolve_dict[running_attr].append( e_ss ) 
            elif e_ss in ('-','+','--minus--'): # -- set oprator in the middle of a list; take it and fix later
                try:             resolve_dict[running_attr].append( e_ss ) 
                except KeyError: failures.append( e_ss )
            else:
                failures.append( e_ss )

    resolved = []
    for attr,vals in resolve_dict.items():
        if attr == 'version':
            if featuresQ: attr = 'ResolutionVersion'
            else        : attr = 'VersionReported'

        val_str = ','.join( vals )
        val_str = re.sub( r',(\-|but_not),',   ' - ', val_str ) # -- fix set operators that has crept in the list
        val_str = re.sub( r',(\+|--minus--),', r'\1', val_str ) # -- e.g. "shirald but not carlosy" might have become "shirald,-,carlosy"
        resolved.append( attr + ':' + val_str )

    return resolved, failures


def merge_query_elements( query_elem_list, format='dict' ):
    """
    Merge attr:val pairs. Those differ by case get merged together (e.g. Priority:1, priority:2 => Priority:1,2)
    This returns a dictionary by default. If format='list', this will return the merged list of attr:val pairs
    """
    elemRE, upperRE = re.compile( r'([^:]+):(.*)' ), re.compile( r'[A-Z]' )
    resolved_lower_case, resolved_mixed_case = {}, {}

    for elem in query_elem_list: # -- separate all lower case and mixed case attr 
        oM = elemRE.match( elem )
        attr, val = oM.groups()

        if upperRE.search( attr ):
            target_dict = resolved_mixed_case
        else:
            target_dict = resolved_lower_case

        try:             target_dict[attr] += ',' + val
        except KeyError: target_dict[attr] = val

    resolved_all_dict = {}
    for attr, val in resolved_mixed_case.items():  # -- bring in common (differ only by case) attr from "lower" to "mixed" dicts
        attr_lower = attr.lower()
        if resolved_lower_case.has_key( attr_lower ): 
            val += ','+resolved_lower_case[attr_lower]
            del( resolved_lower_case[attr_lower] )
        resolved_all_dict[attr] = val

    for attr, val in resolved_lower_case.items(): # -- bring in the rest
        resolved_all_dict[attr] = val

    if format == 'list':
        resolved_all_list = []
        for attr, val in resolved_all_dict.items():
            resolved_all_list.append( attr + ':' + val )
        return resolved_all_list
    else:
        return resolved_all_dict


def existsQ( dbc, table, val, any_case=False ):
    """
    check if a value exists in a multi value table such as functional_category, see_also, etc.
    both reference table (e.g. see_also) and assign table (e.g. see_also_assign) have to exist 
    in the normal struction in bugsdb. If the 'name' column of the reference tables is case
    sensitive, this search will be case sensitive
    """
    table_comp  = table+', '+table+'_assign where '+table+'.id='+table+'_assign.'+table+'_id'

    query = "select exists( select 1 from "+table_comp+" and "
    if any_case:
        query += "lower(convert("+table+".name,char))='"+val.lower()+"') as existsQ"
    else:
        query += table+".name='"+val+"') as existsQ"

    cur = dbc.cursor()
    cur.execute( query )
    row = cur.fetchone()
    cur.close()

    return row['existsQ']


def get_most_probable_case( dbc, table, vals_arr ):
    """
    given a list of values of a multi value attribute (e.g. see_also), this returns a dictionary 
    of the most probable cases
    e.g. ['intergrate','nintegrate'] => {'integrate':'Integrate', 'nintegrate':'NIntegrate'}
    both reference table (e.g. see_also) and assign table (e.g. see_also_assign) have to exist 
    in the normal struction in bugsdb. 
    """
    vals_arr_lower = map( str.lower, vals_arr )        # -- all input values in lower case

    # -- fetch all cases. e.g. box, Box, BOX, AbCd, ABCD, Abcd and let most probable one replace the rest
    table_comp  = table+', '+table+'_assign where '+table+'.id='+table+'_assign.'+table+'_id'
    constr_rest = "lower(convert("+table+".name,char)) in ('" + "','".join(vals_arr_lower) + "')"
    query  = "select distinct name, count("+table+"_assign.id) as total from "+table_comp+" and "+constr_rest + " group by name order by total"

    cur = dbc.cursor()
    cur.execute( query )
    rows = cur.fetchall()
    cur.close()

    def ext(a): return a['name']
    vals_all_arr = map( ext, rows ) 

    vals_all_dict = {} 
    for val in vals_all_arr:
        val_lower = val.lower()
        vals_all_dict[ val_lower ] = val

    return vals_all_dict


def fix_case_sensitivity( dbc, query ):
    """
    tries to fix the case of case sensitive attribute values such as functional_area and functionalcategory
    If the particular case is found in the database, that's used; else, the most probable case is used.
    e.g. if 'integrate' is given, 'Integrate' will be used unless 'integrate' itself exists in the table 
    """
    # -- try only for these (case sensitive) attributes
    attr_table = { 'functionalarea':'functional_area', 'functionalcategory':'functional_category', 'seealso':'see_also' }

    known_id_dict = {}
    for attr, vals in KNOWN_IDS.items():
        attr_lower = attr.replace('_','').lower()
        known_id_dict[attr_lower] = vals

    charM = re.compile( r'[a-zA-Z]' )
    for attr, vals in query.items():
        attr_lower = attr.replace('_','').lower()
        if not attr_table.has_key(attr_lower): continue # -- skip if not a case sensitive attribute

        # -- get all available cases. eg. box will fetch  box, Box, BOX, etc..
        vals = re.sub( r'\s+\-\s+', ':', vals.strip('!') ) # -- replace ' - ' with ':' only as a splitting point
        vals_arr = re.split( r'[\!\s,\+:]+', vals )        # -- cannot split with '-' so as to preserver e.g. Front-end

        table = attr_table[ attr_lower ]

        vals_all_dict = None
        for val in vals_arr: # -- go through original values (with case)
            try: # -- check in the set/known values
                if val in known_id_dict[attr_lower]: continue 
            except KeyError: 
                pass
   
            if     not charM.match( val ): continue # -- skip if there are no chars to fix case
            if existsQ( dbc, table, val ): continue # -- accept if exact case of the specified val exists in the database
            if not existsQ( dbc, table, val, any_case=True ): continue # -- give up if no case exists whatsoever in the database

            if vals_all_dict is None: # -- look up for most probably cases, if not done yet
                vals_all_dict = get_most_probable_case( dbc, table, vals_arr )

            try: # -- if not found anywhere, replce with the most probable case
                val_most_prob = vals_all_dict[val.lower()].replace( '-', '__HYPHEN__' )
                query[attr]   = query[attr].replace( '-', '__HYPHEN__' ) 
                val           = val.replace( '-', '__HYPHEN__' ) # -- make it easier to not treat '-' as a word boundary

                query[attr] = re.sub( eval("r'\\b"+val+"\\b'"), lambda m: val_most_prob, query[attr] )
                query[attr] = query[attr].replace( '__HYPHEN__', '-' )
            except KeyError: # -- no case found in the database
                pass

    return query


def parse( query, **opts ):
    """
    parse a less structured bugs search string queries
    Returns: parsed query string, list of words that failed identification
    optional named parameters:
        dbc: database id key or database connection object to bugs database ['bugstats']
        debug: True/[Flase]
        format: return format. Takes ['dict'], 'list', or 'string' 
                and returns {'attr':'val',...},  ['attr=val',...], or 'attr=val&...'
        log: True/[False]
    """
    # Plan: resolve search phrases by free text attributes (summary, problem, description, body)
    #       translate dates (date range specified with ' - ' => '-')
    #       translate basic (only context independed),
    #       ' - ' => '--minus--' for convenience and revert later
    #       first separation of described (attr:vals) and non described terms 
    #       translate patterns such as "related to bug(\d+)"
    #       contract words, identify words, translate (context dependent: is is_not etc..), separate again
    #       try to identify the unresolved tokens
    #       try to identify names (real name => login name)
    #       translate versions
    #       translate action (e.g. resolved by danl on July 12 2014)
    #       try to relate using a few simple conjunctions such as 'is', 'is not', etc.
    #       second separation
    #       run through the rest of words and try to identify
    #       third (last) separation
    #       convert '--minus--' to ' - ' whereever present
    #       If still there are unresolved terms (thought to be not OK) it's a failure

    global QUERY; QUERY = query

    defaults = { 'dbc':'bugstats', 'debug':False, 'format':'dict', 'log':False }
    for key, val in defaults.items():
        try:             dummy     = opts[key]
        except KeyError: opts[key] = defaults[key]

    dbc, debug, log = opts['dbc'], opts['debug'], opts['log']

    if log:
        log_stamp = time.strftime( "[%Y-%m-%d %H:%M:%S]", time.localtime() ) + " " + USER
        fh_query = open("/var/log/bugs/query_parse/queries", "a" )
        fh_query.write( log_stamp + " -\t" + query + "\t" + "===>" + "\t" )

    dbc, newQ = Databases.GetDBC( dbc )

    if debug: 
        print "======================================================================="
        print "INPUT QUERY:", query, "\n"

    query     = query.strip()
    featuresQ = re.search( 'feature', query )

    fill_attribute_name_dict( dbc )
    resolved_query_elems, query_free_text = resolve_free_text_attrs( query )
    if debug: print "After Free Text Phrases::", resolved_query_elems, query_free_text, "\n"

 #  query_free_text = re.sub( r'\s*([:,\s\+])[:,\s\+]*', r'\1', query_free_text ) # -- separate by only one ':', ',', '+', or a space
    query_free_text = re.sub( r'\s*(?<!bugs)([:,\s\+])[:,\s\+]*', r'\1', query_free_text ) # -- separate by only one ':', ',', '+', or a space (if not bugs+)
    query_free_text = re.sub( r'\s*:\s*~\s*'           , r':~', query_free_text ) # -- bring adjacent : ~ together

    query_dates = translate_dates( query_free_text )
    if debug: print "After Date Translation::", query_dates, "\n"

    query_basic = translate_basic( query_dates )
    if debug: print "After Basic Translation::", query_basic, "\n"

    query_basic = re.sub( r'\s+\-\s+', '--minus--', query_basic ) # -- this will be reverted later, make sure date1 - date2 => date1-date2 before this point

    resolved_1, non_resolved_1 = separate_described_segments( query_basic )
    resolved_query_elems.extend( resolved_1 )
    if debug:
        print "After 1st separation:"
        print "    Resolved:", resolved_1
        print "    Non Resolved:", non_resolved_1, "\n"

    query_rest_1 = ' '.join(non_resolved_1)

    query_pattern = translate_pattern( query_rest_1 )
    if debug: print "After Pattern Translation::", query_pattern, "\n"

    query_contr = contract_parts( dbc, query_pattern )
    if debug: print "After Contraction::", query_contr, "\n"

    fill_value_attr_dic( dbc, query_contr ) # -- move further up as needed
    if debug: print "ID dictionary (1st attempt):", VALUE_INDEX, "\n"

    query = translate_names( dbc, query_contr )
    if debug: print "After translating names::", query, "\n"

    query = translate_versions( query )
    if debug: print "After version tranlation::", query, "\n"

    query = translate_action_pre( query )
    if debug: print "After translating action (pre)::", query, "\n"

    query = translate_action( query )
    if debug: print "After translating action::", query, "\n"

    resolved, non_resolved = separate_described_segments( query )
    resolved_query_elems.extend( resolved )
    query = ' '.join(non_resolved)
    if debug:
        print "After 2nd separation:"
        print "    RESOLVED:", resolved_query_elems
        print "    Non RESOLVED:", non_resolved, "\n"

    query = translate_version_remains( query, featuresQ )
    if debug: print "After translate_version_remains()::", query, "\n"

#   query = translate_versions( query, featuresQ )
#   if debug: print "After version tranlation::", query, "\n"

#   query = translate_action_OLD( query )
#   if debug: print "After action tranlation:", query, "\n"

    query = relate( query )
    if debug: print "After relating:", query, "\n"

    resolved, non_resolved = separate_described_segments( query )
    resolved_query_elems.extend( resolved )
    if debug:
        print "After 3rd separation:"
        print "    RESOLVED:", resolved
        print "    Non RESOLVED:", non_resolved, "\n"

    query_rest = ' '.join(non_resolved)
    resolved, non_resolved = run_through_rest( query_rest, featuresQ )

    resolved_query_elems.extend( resolved )
    non_resolved_words = non_resolved

    if debug:
        print "After run-through and 4th separation:"
        print "    RESOLVED ( IDENTIFIED ):", resolved_query_elems
        print "    Non RESOLVED ( *** ID FAILED *** ):", non_resolved_words, "\n"

    parsed_query_dict = merge_query_elements( resolved_query_elems, 'dict' ) # -- returns a dictionary
    if debug: print "After merging resolved query elemets:", parsed_query_dict, "\n"

    for attr, val in parsed_query_dict.items():
        parsed_query_dict[attr] = val.replace('--minus--',' - ')

    for i, val in enumerate( non_resolved_words ):
        non_resolved_words[i] = val.replace('--minus--',' - ')

    if debug: print "After final preparation:", parsed_query_dict, "\n"

    fix_case_sensitivity( dbc, parsed_query_dict )
    if debug: print "After fixing case:", parsed_query_dict, "\n"

    if opts['format'] in ( 'list', 'string' ):
        parsed_query = []
        for attr, val in parsed_query_dict.items():
            parsed_query.append( attr + '=' + val ) 

        if opts['format'] == 'string':
            parsed_query = '&'.join( parsed_query )
    else: # -- dict
        parsed_query = parsed_query_dict
    
    if debug: 
        print "Parsed:", parsed_query
        print "Failed:", non_resolved_words
        print "======================================================================="

    if newQ: dbc.close()

    if log:
        fh_query.write( parsed_query )

        if non_resolved_words:
            failed_words = ' '.join(non_resolved_words)
            fh_query.write( "\t"+ "***** UNIDENTIFIED WORDS *****" + "\t" + failed_words )

            fh_fail  = open("/var/log/bugs/query_parse/failures", "a" )
            fh_fail.write( log_stamp + " -\t" + query + "\t" + "===>" + "\t" + parsed_query + "\t" + "***** UNIDENTIFIED WORDS *****" + "\t" + failed_words + "\n" )
            fh_fail.close()

        fh_query.write("\n")
        fh_query.close()

    return parsed_query, non_resolved_words


COUNT, SKIP = 0, 0
def test( dbc, query_str, query_dict=None, debug=False ):
    """
    simple function to do testing
    """
    global COUNT, VALUE_INDEX

    COUNT += 1
    if COUNT <= SKIP: return

    VALUE_INDEX = {}

    query_parsed, failed_words = parse(query_str, dbc=dbc, debug=debug )

    pause = True

    if query_dict:
        if query_parsed == query_dict:
            res_desc_left, res_desc_right = '[', ']'
            if not failed_words: pause = False
        else:
            res_desc_left, res_desc_right = '*', '*'
    else:
        res_desc_left, res_desc_right = ' ', ' '

    print res_desc_left +str(COUNT) + res_desc_right, ": ", query_str, "\t===>\t", query_parsed,

    if failed_words:
        print "\t*** UNIDENTIFIED WORDS ***", failed_words,

    print ''

    if pause:
        dummy = sys.stdin.readline() # -- just so control stops and continue on hitting enter


if __name__ == "__main__":
    """
    some tests to check functionality. 
    Run the script by itself to run tests. The script stops for failures.
    Hit 'Enter' to continue
    Usage: SCRIPT_NAME [skip[, debug]]
    """
    try:               SKIP = int( sys.argv[1] )
    except IndexError: SKIP = 0

    try:               debug = sys.argv[2]
    except IndexError: debug = 0

    this_year  = time.strftime( "%Y", time.localtime() )
    last_year  = str( int(this_year) - 1 )
    this_month = time.strftime( "%m", time.localtime() )

    def year_norm( month_num ):
        if int( this_month ) < month_num:
            return last_year
        else:
            return this_year

    try:
        dbc, newQ = Databases.GetDBC( 'bugstats' )

#       test( dbc, "bugs joshs and rbecker reported in October", {}, debug )
        test( dbc, "Mathematica FAIL_IDENTIFYING_THIS", {}, debug )

        ###### EXAMPLES GIVEN ON THE HELP PAGE #####
        test( dbc, "people data reports updated last 7 days", {'LastUpdate': 'last7days', 'FunctionalArea': 'PeopleData'}, debug )
        test( dbc, "Mathematica bugs filed today", {'DateReported': 'today', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "DatabaseLink priority 1 and 2 bugs", {'priority': '1,2', 'FunctionalCategory': 'DatabaseLink', 'ReportType': 'bug'}, debug ) 
        test( dbc, "WolframAlpha unassigned open reports", {'PrimaryDeveloper': 'none', 'Status': 'open', 'Program': 'WolframAlpha'}, debug )
        test( dbc, "Mathematica unprioritized open bugs", {'Status': 'open', 'priority': '0', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug ) 
        test( dbc, "WolframAlpha features whose manager unknown", {'ProjectManager': 'none', 'Program': 'WolframAlpha', 'ReportType': 'feature'}, debug )
        test( dbc, "externally reported DatabaseLink open bugs", {'ReportedBy': 'external', 'Status': 'open', 'ReportType': 'bug', 'FunctionalCategory': 'DatabaseLink'}, debug )
        test( dbc, "Mathematica and WolframDesktop open tag move requests", {'Status': 'open', 'Program': 'Mathematica,WolframDesktop', 'SeeAlso': 'TAGMOVE_REQUESTED'}, debug ) 
        test( dbc, "p1,2 open bugs tagged CNFeedback", {'Priority': '1,2', 'Status': 'open', 'ReportType': 'bug', 'SeeAlso': 'CNFeedback'}, debug )
        test( dbc, "Open Symbolics EricWCheck reports", {'Status': 'Open', 'FunctionalCategory': 'Symbolics', 'SeeAlso': 'EricWCheck'}, debug )

        test( dbc, "p1,2 open Mathematica bugs", {'Priority': '1,2', 'Status': 'open', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs in Mathematica whose priority is 1 or 2 and status is open", {'priority': '1,2', 'status': 'open', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "show me the list of bugs in Mathematica whose priority is 1 or 2 and status is open", {}, debug )

        test( dbc, "ninad open NIntegrate bugs", {'PrimaryDeveloper': 'ninad', 'Status': 'open', 'FunctionalArea': 'NIntegrate', 'ReportType': 'bug'}, debug )
        test( dbc, "eilas open p1 and p2 WolframAlpha features", {'Status': 'open', 'Priority': '1,2', 'ProjectManager': 'eilas', 'Program': 'WolframAlpha', 'ReportType': 'feature'}, debug )
        test( dbc, "carlosy resolved bugs", {'Status': 'resolved', 'QAContact': 'carlosy', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs carlosy resolved", {'ReportType': 'bug', 'ResolvedBy': 'carlosy'}, debug )
        test( dbc, "bugs Rachelle closed last 3 month", {'ReportType': 'bug', 'DateResolveTested': 'last3months', 'ResolveTestedBy': 'rbergman'}, debug )
        test( dbc, "tokarek reports", {'ReportedBy': 'tokarek'}, debug )
        test( dbc, "janed reports", {}, debug )
        test( dbc, "bugs resolved by bugs last year", {'DateResolved': 'lastyear', 'ReportType': 'bug', 'ResolvedBy': 'bugs'}, debug )

        test( dbc, "brettc p1,2 open Visualization bugs", {'Priority': '1,2', 'Status': 'open', 'PrimaryDeveloper': 'brettc', 'ReportType': 'bug', 'FunctionalCategory': 'Visualization'}, debug )
        test( dbc, "manager brettc p1,2 open Visualization bugs", {'ProjectManager': 'brettc', 'Priority': '1,2', 'ReportType': 'bug', 'FunctionalCategory': 'Visualization', 'Status': 'open'}, debug )
        test( dbc, "manager:brettc p1,2 open Visualization bugs", {'ProjectManager': 'brettc', 'Priority': '1,2', 'ReportType': 'bug', 'FunctionalCategory': 'Visualization', 'Status': 'open'}, debug )

        test( dbc, "bugs I filed last 2 weeks", {'ReportedBy': USER, 'DateReported': 'last2weeks', 'ReportType': 'bug'}, debug )
        test( dbc, "my open p1 bugs", {'ReportedBy': 'bugs', 'Status': 'open', 'Priority': '1', 'ReportType': 'bug'}, debug ) # -- pass for bugs

        test( dbc, "Mathematica 10.0 p1 open bugs", {'Priority': '1', 'Status': 'open', 'VersionReported': '10.0', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "Mathematica 9 p1 closed bugs", {'Priority': '1', 'Status': 'closed', 'VersionReported': '9', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "Mathematica version 10 p1 open bugs", {'Priority': '1', 'Status': 'open', 'VersionReported': '10', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "Mathematica V10 p1 open features", {'Priority': '1', 'Status': 'open', 'ResolutionVersion': '10', 'ReportType': 'feature', 'Program': 'Mathematica'}, debug )
        test( dbc, "Mathematica bugs whose version > 10.0.1", {'VersionReported': '>10.0.1', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )

        test( dbc, "bugs I filed on July 10th", {'ReportedBy': USER, 'DateReported': '20140710', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs filed on 20140710",  {'DateReported': '20140710', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs iliang closed in July", {'ReportType': 'bug', 'DateResolveTested': '20140701-20140731', 'ResolveTestedBy': 'iliang'}, debug )
        test( dbc, "Mathematica version 10.0.1 bugs resolved last 30 days", {'DateResolved': 'last30days', 'VersionReported': '10.0.1', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "Mathematica bugs resolved from Feb 1 to Feb 15 2013", {'DateResolved': 'from20130201to20130215', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "Mathematica bugs fixed from Feb 1 to Feb 15 2013", {'DateResolved': 'from20130201to20130215', 'Program': 'Mathematica', 'ReportType': 'bug', 'Resolution':'Fixed'}, debug )
        test( dbc, "WolframAlpha parser bugs updated within the last 7 days",     {'LastUpdate': 'last7days', 'Program': 'WolframAlpha', 'Component': 'parser', 'ReportType': 'bug'}, debug )

        test( dbc, "WolframAlpha reports with summary:+Hurricane +Location", {'Program': 'WolframAlpha', 'summary': '+Hurricane +Location'}, debug )
        test( dbc, "WolframAlpha summary:+Hurricane +Location", {'Program': 'WolframAlpha', 'summary': '+Hurricane +Location'}, debug )
        test( dbc, "summary:+Hurricane +Location -- WolframAlpha", {'Program': 'WolframAlpha', 'summary': '+Hurricane +Location'}, debug )
        test( dbc, "summary:+Hurricane +Location Program:WolframAlpha", {'Program': 'WolframAlpha', 'summary': '+Hurricane +Location'}, debug )
        test( dbc, "summary:+Hurricane +Location program:WolframAlpha", {'program': 'WolframAlpha', 'summary': '+Hurricane +Location'}, debug )
        test( dbc, "problem:+Hurricane +Location Program:WolframAlpha", {'problem': '+Hurricane +Location', 'Program': 'WolframAlpha'}, debug )
        test( dbc, "description:+Hurricane +Location -- WolframAlpha", {'Program': 'WolframAlpha', 'description': '+Hurricane +Location'}, debug )
        test( dbc, "summary:~ Do[*] -- Open", {'Status': 'Open', 'summary': '~Do[*]'}, debug )

        test( dbc, "priority 1 Visualization bugs whose status is not closed", {'status': '!closed', 'FunctionalCategory': 'Visualization', 'ReportType': 'bug', 'priority': '1'}, debug )

        test( dbc, "reports that chadk resolved whose report type is not feature", {'ReportType': '!feature', 'ResolvedBy': 'chadk'}, debug )
        test( dbc, "non features chadk resolved", {'ReportType': '!feature', 'ResolvedBy': 'chadk'}, debug )
        test( dbc, "reports chadk resolved ReportType:!Feature", {'ReportType': '!Feature', 'ResolvedBy': 'chadk'}, debug )

        test( dbc, "Front-end p1 open bugs tester:kurtg,seanc", {'Priority': '1', 'Status': 'open', 'QAContact': 'kurtg,seanc', 'Component': 'Front-end', 'ReportType': 'bug'}, debug )
        test( dbc, "Front-end p1,2 open bugs tester:kurtg+seanc", {'Priority': '1,2', 'Status': 'open', 'QAContact': 'kurtg+seanc', 'Component': 'Front-end', 'ReportType': 'bug'}, debug )
        test( dbc, "Front-end p1 open bugs tester:kurtg - seanc", {'Priority': '1', 'Status': 'open', 'QAContact': 'kurtg - seanc', 'Component': 'Front-end', 'ReportType': 'bug'}, debug )
        ###### END EXAMPLES ON THE HELP PAGE

        test( dbc, "stefanr bugs updated last 30 days", {'LastUpdate': 'last30days', 'QAContact': 'stefanr', 'ReportType': 'bug'}, debug )
        test( dbc, "stefanr bugs updated in the last 30 days", {'LastUpdate': 'last30days', 'QAContact': 'stefanr', 'ReportType': 'bug'}, debug )

        test( dbc, "pending tag moves", {'SeeAlso': 'TAGMOVE_REQUESTED'}, debug )
        test( dbc, "tag move requests", {'SeeAlso': 'TAGMOVE_REQUESTED'}, debug )
        test( dbc, "tag moves", {'SeeAlso': 'TAG_MOVED'}, debug )
        test( dbc, "tag move rejects", {'SeeAlso': 'TAGMOVE_REJECTED'}, debug )

        test( dbc, "my resolved bugs", {'ReportedBy': USER, 'Status': 'resolved', 'ReportType': 'bug'} , debug) 
        test( dbc, "carlosy priority one resolved bugs", {'Status': 'resolved', 'priority': '1', 'QAContact': 'carlosy', 'ReportType': 'bug'} , debug) 
        test( dbc, "open Mathematica tag move requests", {'Status': 'open', 'Program': 'Mathematica', 'SeeAlso': 'TAGMOVE_REQUESTED'} , debug) 
        test( dbc, "Mathematica and WolframDesktop open tag move requests", {'Status': 'open', 'Program': 'Mathematica,WolframDesktop', 'SeeAlso': 'TAGMOVE_REQUESTED'} , debug) 
        test( dbc, "Mathematica bugs filed from August 1st", {'DateReported': 'from20140801', 'Program': 'Mathematica', 'ReportType': 'bug'} , debug) 
        test( dbc, "Mathematica bugs filed since Aug 1st", {'DateReported': 'since20140801', 'Program': 'Mathematica', 'ReportType': 'bug'} , debug) 
        test( dbc, "Mathematica bugs filed since 20140801", {'DateReported': 'since20140801', 'Program': 'Mathematica', 'ReportType': 'bug'} , debug) 


        test( dbc, "developer minhsuanp manager brettc tester robertc", {'PrimaryDeveloper': 'minhsuanp', 'ProjectManager': 'brettc', 'QAContact': 'robertc'} , debug) 
        test( dbc, "minhsuanp robertc open priority 1 and 2 bugs", {'PrimaryDeveloper': 'minhsuanp', 'Status': 'open', 'priority': '1,2', 'ReportType': 'bug', 'QAContact': 'robertc'} , debug) 
        test( dbc, "minhsuanp robertc open p1, 2 and 3 bugs", {'PrimaryDeveloper': 'minhsuanp', 'Status': 'open', 'Priority': '1,2,3', 'ReportType': 'bug', 'QAContact': 'robertc'} , debug) 
        test( dbc, "minhsuanp open p1 and p2 bugs", {'PrimaryDeveloper': 'minhsuanp', 'Status': 'open', 'Priority': '1,2', 'ReportType': 'bug'} , debug) 
        test( dbc, "rknapp open 10.1 bugs", {'PrimaryDeveloper': 'rknapp', 'Status': 'open', 'VersionReported': '10.1', 'ReportType': 'bug'} , debug) 
        test( dbc, "rknapp open 10.1.0 bugs", {'PrimaryDeveloper': 'rknapp', 'Status': 'open', 'VersionReported': '10.1.0', 'ReportType': 'bug'} , debug) 


        test( dbc, "Mathematica version 10.0.1 bugs reported yesterday", {'DateReported': 'yesterday', 'VersionReported': '10.0.1', 'Program': 'Mathematica', 'ReportType': 'bug'} , debug) 
        test( dbc, "Mathematica version V10 bugs reported by carlosy", {'ReportedBy': 'carlosy', 'VersionReported': '10', 'Program': 'Mathematica', 'ReportType': 'bug'} , debug) 
        test( dbc, "Mathematica bugs with  version < 10", {'VersionReported': '<10', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "Mathematica bugs whose version < 10", {'VersionReported': '<10', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )

        test( dbc, "bugs bbhatt resolved", {'ReportType': 'bug', 'ResolvedBy': 'bbhatt'}, debug )
        test( dbc, "bugs bbhatt resolved in Mathematica", {'Program': 'Mathematica', 'ReportType': 'bug', 'ResolvedBy': 'bbhatt'}, debug )
        test( dbc, "Mathematica bugs bbhatt resolved", {'Program': 'Mathematica', 'ReportType': 'bug', 'ResolvedBy': 'bbhatt'}, debug )
        test( dbc, "bugs bbhatt resolved in last two weeks", {'DateResolved': 'last2weeks', 'ReportType': 'bug', 'ResolvedBy': 'bbhatt'}, debug )
        test( dbc, "bbhatt resolved bugs", {'Status': 'resolved', 'QAContact': 'bbhatt', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs bbhatt resolved last week", {'DateResolved': 'lastweek', 'ReportType': 'bug', 'ResolvedBy': 'bbhatt'}, debug )
        test( dbc, "bugs bbhatt closed during last two weeks", {'ReportType': 'bug', 'DateResolveTested': 'last2weeks', 'ResolveTestedBy': 'bbhatt'}, debug )
        test( dbc, "Mathematica bugs reported by carlosy today", {'ReportedBy': 'carlosy', 'DateReported': 'today', 'Program': 'Mathematica', 'ReportType': 'bug'} , debug )
        test( dbc, "bugs iliang closed last July", {'ReportType': 'bug', 'DateResolveTested': '20140701-20140731', 'ResolveTestedBy': 'iliang'}, debug )
        test( dbc, "bugs iliang closed in last July", {'ReportType': 'bug', 'DateResolveTested': '20140701-20140731', 'ResolveTestedBy': 'iliang'}, debug )
        test( dbc, "bugs iliang closed in 2010", {'ReportType': 'bug', 'DateResolveTested': '20100101-20101231', 'ResolveTestedBy': 'iliang'}, debug )
        test( dbc, "bugs iliang closed in Jan 2010", {'ReportType': 'bug', 'DateResolveTested': '20100101-20100131', 'ResolveTestedBy': 'iliang'}, debug )
        test( dbc, "Mathematica bugs carlosy reported today", {'ReportedBy': 'carlosy', 'DateReported': 'today', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "P1 Mathematica bugs reported by carlosy last month", {'ReportedBy': 'carlosy', 'DateReported': 'lastmonth', 'Priority': '1', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs I reported last week", {'ReportedBy': USER, 'DateReported': 'lastweek', 'ReportType': 'bug'} , debug) 

        last_Mon = Databases.GetLastWeekday( "Monday" )
        last_Tue = Databases.GetLastWeekday( "Tuesday" )
        last_Wed = Databases.GetLastWeekday( "Wednesday" )
        last_Thu = Databases.GetLastWeekday( "Thursday" )
        last_Fri = Databases.GetLastWeekday( "Friday" )

        test( dbc, "Mathematica bugs resolved on last Monday", {'DateResolved': str(last_Mon), 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "Mathematica bugs resolved last Tuesday", {'DateResolved': str(last_Tue), 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "Mathematica bugs resolved since last Wednesday", {'DateResolved': 'since'+str(last_Wed), 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "Mathematica bugs resolved since Wednesday", {'DateResolved': 'since'+str(last_Wed), 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "danielf open bugs updated before last Monday", {'PrimaryDeveloper': 'danielf', 'Status': 'open', 'ReportType': 'bug', 'LastUpdate': 'before'+str(last_Mon)}, debug )
        test( dbc, "danielf open bugs updated on or before last Monday", {'PrimaryDeveloper': 'danielf', 'Status': 'open', 'ReportType': 'bug', 'LastUpdate': 'onorbefore'+str(last_Mon)}, debug )
        test( dbc, "danielf open bugs updated on or before Monday", {'PrimaryDeveloper': 'danielf', 'Status': 'open', 'ReportType': 'bug', 'LastUpdate': 'onorbefore'+str(last_Mon)}, debug )
        test( dbc, "erinc WolframAlpha Open Priority 1,2 bugs updated since friday", {'PrimaryDeveloper': 'erinc', 'Status': 'Open', 'LastUpdate': 'since'+str(last_Fri), 'Priority': '1,2', 'Program': 'WolframAlpha', 'ReportType': 'bug'}, debug )

        test( dbc, "brettc priority 1 and 2 visualization bugs", {'priority': '1,2', 'FunctionalCategory': 'Visualization', 'PrimaryDeveloper': 'brettc', 'ReportType': 'bug'} , debug) 
        test( dbc, "itais priority 1, 2 and 3 version 10 wolfram alpha open features", {'PrimaryDeveloper': 'itais', 'Status': 'open', 'priority': '1,2,3', 'Program': 'WolframAlpha', 'ReportType': 'feature', 'ResolutionVersion': '10'} , debug) 
        test( dbc, "itais priority 1, 2 and 3 version 10 alpha open features", {'PrimaryDeveloper': 'itais', 'Status': 'open', 'priority': '1,2,3', 'Program': 'WolframAlpha', 'ReportType': 'feature', 'ResolutionVersion': '10'} , debug) 
        test( dbc, "summary: +hurricane +location -- open priority 1 bugs", {'Status': 'open', 'priority': '1', 'ReportType': 'bug', 'summary': '+hurricane +location'} , debug) 

        test( dbc, "alpha p1 open bugs", {'Priority': '1', 'Status': 'open', 'Program': 'WolframAlpha', 'ReportType': 'bug'}, debug )
        test( dbc, "wolfram alpha p1 open bugs", {'Priority': '1', 'Status': 'open', 'Program': 'WolframAlpha', 'ReportType': 'bug'}, debug )
        test( dbc, "wolframalpha p1 open bugs", {'Priority': '1', 'Status': 'open', 'Program': 'WolframAlpha', 'ReportType': 'bug'}, debug )
        test( dbc, "p1 open alpha bugs", {'Priority': '1', 'Status': 'open', 'Program': 'WolframAlpha', 'ReportType': 'bug'}, debug )
        test( dbc, "p1 open wolfram alpha bugs", {'Priority': '1', 'Status': 'open', 'Program': 'WolframAlpha', 'ReportType': 'bug'}, debug )
        test( dbc, "p1 open bugs of alpha", {'Priority': '1', 'Status': 'open', 'Program': 'WolframAlpha', 'ReportType': 'bug'}, debug )
        test( dbc, "p1 open bugs of wolfram alpha", {'Priority': '1', 'Status': 'open', 'Program': 'WolframAlpha', 'ReportType': 'bug'}, debug )

        test( dbc, "Mathematica bugs I reported from July 10 to 15", {'ReportedBy': USER, 'DateReported': 'from20140710to20140715', 'Program': 'Mathematica', 'ReportType': 'bug'} , debug) 
        test( dbc, "WolframAlpha reports resolved from July 10 to July 15 2013", {'DateResolved': 'from20130710to20130715', 'Program': 'WolframAlpha'} , debug) 
        test( dbc, "Mathematica bugs filed in July, 2012 by bugs", {'ReportedBy': 'bugs', 'DateReported': '20120701-20120731', 'Program': 'Mathematica', 'ReportType': 'bug'} , debug) 
        test( dbc, "reports shirald filed in December", {'ReportedBy': 'shirald', 'DateReported': year_norm(12)+'1201-'+year_norm(12)+'1231'}, debug )
        test( dbc, "Mathematica bugs closed by bugs in June", {'Program': 'Mathematica', 'ReportType': 'bug', 'DateResolveTested': '20140601-20140630', 'ResolveTestedBy': 'bugs'} , debug) 
        test( dbc, "reports closed by bugs in July 2012", {'DateResolveTested': '20120701-20120731', 'ResolveTestedBy': 'bugs'} , debug) 
        test( dbc, "Mathematica reports resolved from June 25 to July 5 2013 by carlosy", {'DateResolved': 'from20130625to20130705', 'Program': 'Mathematica', 'ResolvedBy': 'carlosy'} , debug) 
        test( dbc, "bugs resolved from June 25 to July 5 2013", {'DateResolved': 'from20130625to20130705', 'ReportType': 'bug'}, debug )
        test( dbc, "Mathematica reports I resolved from June 25 to July 5", {'DateResolved': 'from20140625to20140705', 'Program': 'Mathematica', 'ResolvedBy': USER} , debug) 
        test( dbc, "Mathematica reports resolved between Aug 10 and 15, 2012", {'DateResolved': 'between20120810and20120815', 'Program': 'Mathematica'} , debug) 
        test( dbc, "Mathematica reports resolved between Aug 10 and 15", {'DateResolved': 'between20140810and20140815', 'Program': 'Mathematica'} , debug) 
        test( dbc, "bugs filed from July 10, 2012 to July 15 2012", {'DateReported': 'from20120710to20120715', 'ReportType': 'bug'} , debug) 
        test( dbc, "Mathematica bugs filed in July", {'DateReported': '20140701-20140731', 'Program': 'Mathematica', 'ReportType': 'bug'} , debug) 
        test( dbc, "Mathematica bugs filed in July, 2012", {'DateReported': '20120701-20120731', 'Program': 'Mathematica', 'ReportType': 'bug'} , debug) 
        test( dbc, "Mathematica bugs filed in July, 2012 ReportedBy:bugs", {'ReportedBy': 'bugs', 'DateReported': '20120701-20120731', 'Program': 'Mathematica', 'ReportType': 'bug'} , debug) 
        test( dbc, "WolframAlpha and Mathematica bugs reported in March", {'DateReported': '20140301-20140331', 'Program': 'WolframAlpha,Mathematica', 'ReportType': 'bug'} , debug) 
        test( dbc, "Program:Mathematica program WolframAlpha  MathematicaPlayer bugs reported yesterday", {'DateReported': 'yesterday', 'Program': 'Mathematica,WolframAlpha,MathematicaPlayer', 'ReportType': 'bug'} , debug) 


        test( dbc, "developer:brettc priority 1 and 2 visualization bugs", {'PrimaryDeveloper': 'brettc', 'FunctionalCategory': 'Visualization', 'ReportType': 'bug', 'priority': '1,2'} , debug) 
        test( dbc, "reporter brettc priority 1 and 2 visualization bugs", {'ReportedBy': 'brettc', 'FunctionalCategory': 'Visualization', 'ReportType': 'bug', 'priority': '1,2'} , debug) 
        test( dbc, "devel is rknapp manager eilas tester shirald and status is not closed", {'PrimaryDeveloper': 'rknapp', 'status': '!closed', 'ProjectManager': 'eilas', 'QAContact': 'shirald'} , debug) 
        test( dbc, "devel rknapp manager eilas tester shirald and status not closed", {'PrimaryDeveloper': 'rknapp', 'status': '!closed', 'ProjectManager': 'eilas', 'QAContact': 'shirald'} , debug) 
        test( dbc, "priority 1 and 2 summary:this is a D0[*] test problem: this is a problem devel: rknapp SeeAlso : ~ ShowStopper status is not closed reported between July 01 and Aug 1 qacontact:shirald - carlosy version  <  10.0.0.14", {'PrimaryDeveloper': 'rknapp', 'status': '!closed', 'VersionReported': '<10.0.0.14', 'summary': 'this is a D0[*] test', 'priority': '1,2', 'DateReported': 'between20140701and20140801', 'problem': 'this is a problem', 'QAContact': 'shirald - carlosy', 'SeeAlso': '~ShowStopper'} , debug) 
        test( dbc, "summary~add numbers -- WolframAlpha PacletData  resolved reports", {'Status': 'resolved', 'Program': 'WolframAlpha', 'Component': 'PacletData', 'summary': '~add numbers'} , debug) 
        test( dbc, "summary~add numbers program:WolframAlpha PacletData  resolved reports", {'Status': 'resolved', 'program': 'WolframAlpha', 'Component': 'PacletData', 'summary': '~add numbers'} , debug) 
        test( dbc, "WolframAlpha PacletData  resolved reports summary~add numbers", {'Status': 'resolved', 'Program': 'WolframAlpha', 'Component': 'PacletData', 'summary': '~add numbers'} , debug) 
        test( dbc, "carlosy non Feature resolved reports with tag TAG_MOVED", {'Status': 'resolved', 'QAContact': 'carlosy', 'ReportType': '!Feature', 'SeeAlso': 'TAG_MOVED'} , debug) 
        test( dbc, "rajb's resolved non features", {'Status': 'resolved', 'QAContact': 'rajb', 'ReportType': '!feature'} , debug) 
#       test( dbc, "open Graphics t-charts bugs", {'Status': 'open', 'FunctionalCategory': 'Graphics', 'PrimaryDeveloper': 't-charts', 'ReportType': 'bug'} , debug) 
        test( dbc, "open Graphics t-charts bugs", {'Status': 'open', 'FunctionalArea':     'Graphics', 'PrimaryDeveloper': 't-charts', 'ReportType': 'bug'} , debug) 
        test( dbc, "ProfessionalVersion  Priority 1 WolframCalculate", {'Priority': '1', 'Program': 'WolframCalculate', 'Component': 'ProfessionalVersion'} , debug) 


        test( dbc, "t-alpha-parsermanager reports", {'ProjectManager': 't-alpha-parsermanager'} , debug) 
        test( dbc, "unassigned WolframAlpha reports", {'PrimaryDeveloper': 'none', 'Program': 'WolframAlpha'} , debug) 
        test( dbc, "WolframCalculate Manager unknown", {'ProjectManager': 'none', 'Program': 'WolframCalculate'} , debug) 
        test( dbc, "unprioritized WolframCalculate", {'priority': '0', 'Program': 'WolframCalculate'} , debug) 
        test( dbc, "Parser ShowStopper", {'Component': 'Parser', 'SeeAlso': 'ShowStopper'} , debug) 
        test( dbc, "t-alpha-naturalsciencemanager  WolframAlpha", {'PrimaryDeveloper': 't-alpha-naturalsciencemanager', 'Program': 'WolframAlpha'} , debug) 
        test( dbc, "WolframProblemGenerator reports", {'Program': 'WolframProblemGenerator'} , debug) 


        test( dbc, "open bugs I reported", {'ReportedBy': USER, 'Status': 'open', 'ReportType': 'bug'} , debug) 
        test( dbc, "bugs I reported and still open", {'ReportedBy': USER, 'Status': 'open', 'ReportType': 'bug'} , debug) 
        test( dbc, "iliang's ProbabilityAndStatistics  resolved bugs", {'Status': 'resolved', 'FunctionalCategory': 'ProbabilityAndStatistics', 'QAContact': 'iliang', 'ReportType': 'bug'} , debug) 
        test( dbc, "iliang's resolved mathematica non features", {'Status': 'resolved', 'QAContact': 'iliang', 'ReportType': '!feature', 'Program': 'mathematica'} , debug) 
        test( dbc, "open bugs boyangc reported", {'ReportedBy': 'boyangc', 'Status': 'open', 'ReportType': 'bug'} , debug) 
        test( dbc, "xiaofeng non feature resolved reports", {'PrimaryDeveloper': 'xiaofeng', 'Status': 'resolved', 'ReportType': '!feature'} , debug) 
        test( dbc, "stefanr's priority 1 and 2 resolved reports", {'Status': 'resolved', 'priority': '1,2', 'QAContact': 'stefanr'} , debug) 
        test( dbc, "resolved ChineseVersion bugs", {'Status': 'resolved', 'ReportType': 'bug', 'SeeAlso': 'ChineseVersion'} , debug) 
        test( dbc, "Visualization bugs reported by shirald on July 1", {'ReportedBy': 'shirald', 'DateReported': '20140701', 'ReportType': 'bug', 'FunctionalCategory': 'Visualization'} , debug) 
        test( dbc, "Visualization bugs reported today by shirald", {'ReportedBy': 'shirald', 'DateReported': 'today', 'ReportType': 'bug', 'FunctionalCategory': 'Visualization'} , debug) 
        test( dbc, "V10 Visualization features reported yesterday QAContact:shirald - carlosy", {'DateReported': 'yesterday', 'ResolutionVersion': '10', 'QAContact': 'shirald - carlosy', 'ReportType': 'feature', 'FunctionalCategory': 'Visualization'} , debug) 
        test( dbc, "developer: rknapp project manager eilas qa contact carlosy", {'PrimaryDeveloper': 'rknapp', 'ProjectManager': 'eilas', 'QAContact': 'carlosy'} , debug) 
        test( dbc, "Developer: rknapp qacontact shirald date reported 20140302", {'PrimaryDeveloper': 'rknapp', 'datereported': '20140302', 'QAContact': 'shirald'} , debug) 
        test( dbc, "Developer: rknapp qacontact:shirald reported 20140302", {'PrimaryDeveloper': 'rknapp', 'DateReported': '20140302', 'QAContact': 'shirald'} , debug) 
        test( dbc, "Primary Developer: rknapp date resolved 20140302", {'PrimaryDeveloper': 'rknapp', 'dateresolved': '20140302'} , debug) 
        test( dbc, "primaryDeveloper: rknapp last updated 20140302", {'PrimaryDeveloper': 'rknapp', 'LastUpdate': '20140302'} , debug) 
        test( dbc, "CloudObject bugs opened last three weeks", {'DateReported': 'last3weeks', 'FunctionalArea': 'CloudObject', 'ReportType': 'bug'} , debug) 


        test( dbc, "developer: rknapp last updated 20140102 priority 1,2,3 import export qa contact shirald , carlosy reported by me ", {'PrimaryDeveloper': 'rknapp', 'LastUpdate': '20140102', 'ReportedBy': USER, 'priority': '1,2,3', 'FunctionalCategory': 'ImportExport', 'QAContact': 'shirald,carlosy'} , debug) 
        test( dbc, "rknapp report type crash wrong behavior and status open,resolved unprioritized ReportedBy: shirald, iliang + carlosy - kurtg", {'ReportedBy': 'shirald,iliang+carlosy - kurtg', 'PrimaryDeveloper': 'rknapp', 'status': 'open,resolved', 'ReportType': 'crash,wrongbehavior,', 'priority': '0'}, debug )
        test( dbc, "bugs priority 1 and 2 QAContact:shirald,bugs I reported yesterday July 1, 2014 and Aug11,2014", {'ReportedBy': 'bugs', 'DateReported': 'yesterday,20140701,20140811', 'QAContact': 'shirald,bugs', 'ReportType': 'bug', 'priority': '1,2'} , debug) 
        test( dbc, "Mathematica priority 1 and 2 functionalarea:AND import export bugs QAContact:shirald,bugs I reported yesterday July 1 and Aug11,2014", {'FunctionalArea': 'AND', 'ReportedBy': USER, 'priority': '1,2', 'DateReported': 'yesterday,20140701,20140811', 'Program': 'Mathematica', 'ReportType': 'bug', 'FunctionalCategory': 'ImportExport', 'QAContact': 'shirald,bugs'} , debug) 
        test( dbc, "bugs priority 1 and 2 QAContact:shirald,bugs I closed between February 23, 2013 and Jun 1, 2014", {'priority': '1,2', 'QAContact': 'shirald,bugs', 'ReportType': 'bug', 'DateResolveTested': 'between20130223and20140601', 'ResolveTestedBy': USER} , debug) 
        test( dbc, "bugs priority 1 and 2 QAContact:shirald,bugs I closed before yesterday", {'priority': '1,2', 'QAContact': 'shirald,bugs', 'ReportType': 'bug', 'DateResolveTested': 'beforeyesterday', 'ResolveTestedBy': USER} , debug) 
        test( dbc, "bugs priority 1 and 2 QAContact:shirald,bugs reported today", {'priority': '1,2', 'DateReported': 'today', 'QAContact': 'shirald,bugs', 'ReportType': 'bug'} , debug) 
        test( dbc, "my priority 1 and 2 open bugs", {'ReportedBy': USER, 'Status': 'open', 'ReportType': 'bug', 'priority': '1,2'} , debug) 
        test( dbc, "EricWCheck", {'SeeAlso': 'EricWCheck'} , debug) 
        test( dbc, "Mathematica priority 1 and 2 bugs externally reported", {'ReportedBy': 'external', 'priority': '1,2', 'Program': 'Mathematica', 'ReportType': 'bug'} , debug) 
        test( dbc, "my priority 1 and 2 bugs with resolution version < 8.1.0", {'ReportedBy': USER, 'priority': '1,2', 'resolutionversion': '<8.1.0', 'ReportType': 'bug'} , debug) 
        test( dbc, "WolframAlpha bugs whose manager is none", {'ProjectManager': 'none', 'Program': 'WolframAlpha', 'ReportType': 'bug'} , debug) 
        test( dbc, "WolframAlpha bugs without managers", {'ProjectManager': 'none', 'Program': 'WolframAlpha', 'ReportType': 'bug'} , debug) 
        test( dbc, "WolframAlpha bugs without a manager", {'ProjectManager': 'none', 'Program': 'WolframAlpha', 'ReportType': 'bug'} , debug) 
        test( dbc, "WolframAlpha bugs with no manager", {'ProjectManager': 'none', 'Program': 'WolframAlpha', 'ReportType': 'bug'} , debug) 
        test( dbc, "WolframAlpha bugs with no managers", {'ProjectManager': 'none', 'Program': 'WolframAlpha', 'ReportType': 'bug'} , debug) 
        test( dbc, "WolframAlpha bugs with no testers", {'QAContact': 'none', 'Program': 'WolframAlpha', 'ReportType': 'bug'} , debug) 
        test( dbc, "WolframAlpha bugs whose manager unknown", {'ProjectManager': 'none', 'Program': 'WolframAlpha', 'ReportType': 'bug'} , debug) 

        test( dbc, "unprioritized WolframAlpha bugs", {'priority': '0', 'Program': 'WolframAlpha', 'ReportType': 'bug'} , debug) 
        test( dbc, "unassigned WolframAlpha bugs", {'PrimaryDeveloper': 'none', 'Program': 'WolframAlpha', 'ReportType': 'bug'} , debug) 
        test( dbc, "ghurst WolframProblemGenerator bugs", {'PrimaryDeveloper': 'ghurst', 'Program': 'WolframProblemGenerator', 'ReportType': 'bug'} , debug) 
        test( dbc, "ImageCustomization", {'FunctionalCategory': 'ImageCustomization'} , debug) 
        test( dbc, "shenghuiy  Priority 3 WolframCalculate  bugs with SeeAlso CNFeedback", {'PrimaryDeveloper': 'shenghuiy', 'Priority': '3', 'Program': 'WolframCalculate', 'ReportType': 'bug', 'SeeAlso': 'CNFeedback'} , debug) 
        test( dbc, "shenghuiy  Priority 3 WolframCalculate  bugs with see also tag CNFeedback", {'PrimaryDeveloper': 'shenghuiy', 'Priority': '3', 'Program': 'WolframCalculate', 'ReportType': 'bug', 'SeeAlso': 'CNFeedback'} , debug) 
        test( dbc, "shenghuiy  Priority 3 CNFeedback WolframCalculate bugs", {'PrimaryDeveloper': 'shenghuiy', 'Priority': '3', 'Program': 'WolframCalculate', 'ReportType': 'bug', 'SeeAlso': 'CNFeedback'} , debug) 
        test( dbc, "chadk resolved reports whose report type is not feature", {'Status': 'resolved', 'QAContact': 'chadk', 'ReportType': '!feature'} , debug) 
        test( dbc, "reports chadk resolved whose report type is not feature", {'ReportType': '!feature', 'ResolvedBy': 'chadk'}, debug )
        test( dbc, "reports that chadk resolved whose report type is not feature", {'ReportType': '!feature', 'ResolvedBy': 'chadk'}, debug )
        test( dbc, "chadk non feature resolved reports", {'Status': 'resolved', 'QAContact': 'chadk', 'ReportType': '!feature'} , debug) 
        test( dbc, "non feature reports chadk resolved", {'ReportType': '!feature', 'ResolvedBy': 'chadk'} , debug) 
        test( dbc, "chadk resolved non feature reports", {'Status': 'resolved', 'QAContact': 'chadk', 'ReportType': '!feature'}, debug )
        test( dbc, "my priority 1 and 2 bugs that are not closed", {'Status': '!closed', 'ReportedBy': USER, 'ReportType': 'bug', 'priority': '1,2'} , debug) 
        test( dbc, "unassigned Mathematica open reports", {'PrimaryDeveloper': 'none', 'Status': 'open', 'Program': 'Mathematica'} , debug) 

        test( dbc, "reports updated last week", {'LastUpdate': 'lastweek'} , debug) 
        test( dbc, "Mathematica bugs updated last week", {'LastUpdate': 'lastweek', 'Program': 'Mathematica', 'ReportType': 'bug'} , debug) 
        test( dbc, "Mathematica bugs updated but not reported today", {'LastUpdate': 'today', 'Program': 'Mathematica', 'ReportType': 'bug', 'DateReported': '!today'} , debug) 
        test( dbc, "Mathematica bugs updated but not reported today in V10", {'LastUpdate': 'today', 'VersionReported': '10', 'Program': 'Mathematica', 'ReportType': 'bug', 'DateReported': '!today'} , debug) 
        test( dbc, "Mathematica bugs active within last week", {'LastUpdate': 'lastweek', 'Program': 'Mathematica', 'ReportType': 'bug'} , debug) 
        test( dbc, "reports updated < yesterday", {'LastUpdate': '<yesterday'} , debug) 
        test( dbc, "reports updated on or before yesterday", {'LastUpdate': 'onorbeforeyesterday'} , debug) 
        test( dbc, "Mathematica bugs reported in V10.0.1", {'VersionReported': '10.0.1', 'Program': 'Mathematica', 'ReportType': 'bug'} , debug) 
        test( dbc, "Mathematica bugs reported in 10.0.1", {'VersionReported': '10.0.1', 'Program': 'Mathematica', 'ReportType': 'bug'} , debug) 

        test( dbc, "stefanr open priority 1 and 2 bugs", {'Status': 'open', 'priority': '1,2', 'QAContact': 'stefanr', 'ReportType': 'bug'}, debug )
        test( dbc, "stefanr open priority 1 or  2 bugs", {'Status': 'open', 'priority': '1,2', 'QAContact': 'stefanr', 'ReportType': 'bug'}, debug )
        test( dbc, "my resolved bugs with TAG_MOVED for version 10.0.1", {'ReportedBy': 'bugs', 'Status': 'resolved', 'VersionReported': '10.0.1', 'ReportType': 'bug', 'SeeAlso': 'TAG_MOVED'}, debug )
        test( dbc, "ninad open non Integrate bugs", {'PrimaryDeveloper': 'ninad', 'Status': 'open', 'FunctionalArea': '!Integrate', 'ReportType': 'bug'}, debug )
        test( dbc, "Open WolframAlpha bugs tagged zhP2.5", {'Status': 'Open', 'Program': 'WolframAlpha', 'ReportType': 'bug', 'SeeAlso': 'zhP2.5'}, debug )
        test( dbc, 'summary:"Food-related splats"', {'summary': '"Food-related splats"'}, debug ) 
        test( dbc, "WolframAlpha FoodData problem:Wendy's", {'FunctionalArea': 'FoodData', 'Program': 'WolframAlpha', 'problem': "Wendy's"}, debug )
        test( dbc, "WolframAlpha bugs updated within last 30 days",     {'LastUpdate': 'last30days', 'Program': 'WolframAlpha', 'ReportType': 'bug'}, debug )
        test( dbc, "WolframAlpha bugs updated within the last 30 days", {'LastUpdate': 'last30days', 'Program': 'WolframAlpha', 'ReportType': 'bug'}, debug )
        test( dbc, "WolframAlpha parser bugs updated in last 7 days",     {'LastUpdate': 'last7days', 'Program': 'WolframAlpha', 'Component': 'parser', 'ReportType': 'bug'}, debug )
        test( dbc, "WolframAlpha bugs resolved after August 19", {'DateResolved': 'after20140819', 'Program': 'WolframAlpha', 'ReportType': 'bug'}, debug )
        test( dbc, "brettc open non-Visualization bugs", {'PrimaryDeveloper': 'brettc', 'Status': 'open', 'ReportType': 'bug', 'FunctionalCategory': '!Visualization'}, debug )
        test( dbc, "WolframAlpha Open bugs with developer norikoy but not johnnien", {'Status': 'Open', 'PrimaryDeveloper': 'norikoy - johnnien', 'Program': 'WolframAlpha', 'ReportType': 'bug'}, debug )
        test( dbc, "WolframAlpha Open bugs with developer norikoy and johnnien", {'Status': 'Open', 'PrimaryDeveloper': 'norikoy+johnnien', 'Program': 'WolframAlpha', 'ReportType': 'bug'}, debug )
        test( dbc, "WolframAlpha Open bugs with developer norikoy or johnnien", {'Status': 'Open', 'PrimaryDeveloper': 'norikoy,johnnien', 'Program': 'WolframAlpha', 'ReportType': 'bug'}, debug )
        test( dbc, "WolframAlpha Resolved as Irreproducible bugs resolved before August 19 2014", {'Status':'Resolved', 'DateResolved': 'before20140819', 'Program': 'WolframAlpha', 'ReportType': 'bug', 'Resolution': 'Irreproducible'}, debug )

        # -- Fix case sesitivity
        test( dbc, "open visualization bugs", {'Status': 'open', 'FunctionalCategory': 'Visualization', 'ReportType': 'bug'}, debug )
        test( dbc, "brettc open non visualization bugs", {'Status': 'open', 'FunctionalCategory': '!Visualization', 'PrimaryDeveloper': 'brettc', 'ReportType': 'bug'}, debug )
        test( dbc, "open pink and box bugs", {'Status': 'open', 'FunctionalArea': 'Pink,Box', 'ReportType': 'bug'}, debug ) 
        test( dbc, "open FunctionalArea:!pink+box - visualization,pink-floyd,front-end bugs", {'Status': 'open', 'FunctionalArea': '!Pink+Box - Visualization,pink-floyd,Front-end', 'ReportType': 'bug'}, debug )
        test( dbc, "open FunctionalArea:graphics,utf-8,front-END FunctionalCategory:graphics bugs", {'Status': 'open', 'FunctionalCategory': 'Graphics', 'FunctionalArea': 'graphics,UTF-8,Front-end', 'ReportType': 'bug'}, debug ) # -- FArea table does have 'graphics'; so doesn't get fixed
        test( dbc, "open FunctionalArea:pink - box,front-END bugs", {'Status': 'open', 'FunctionalArea': 'Pink - Box,Front-end', 'ReportType': 'bug' }, debug )
        test( dbc, "danielf open bugs updated since 20140826", {'PrimaryDeveloper': 'danielf', 'Status': 'open', 'ReportType': 'bug', 'LastUpdate': 'since20140826'}, debug )
        test( dbc, "danielf open bugs updated on or before 20140826", {'PrimaryDeveloper': 'danielf', 'Status': 'open', 'ReportType': 'bug', 'LastUpdate': 'onorbefore20140826'}, debug )
        # -- various date formats
        test( dbc, "bugs robertc resolved since Sep 15", {'DateResolved': 'since20140915', 'ReportType': 'bug', 'ResolvedBy': 'robertc'}, debug )
        test( dbc, "bugs robertc resolved since 20140915", {'DateResolved': 'since20140915', 'ReportType': 'bug', 'ResolvedBy': 'robertc'}, debug )
        test( dbc, "bugs robertc resolved since 2014-09-05", {'DateResolved': 'since20140905', 'ReportType': 'bug', 'ResolvedBy': 'robertc'}, debug )
        test( dbc, "bugs robertc resolved between 2014/9/5 and 2014-09-15", {'DateResolved': 'between20140905and20140915', 'ReportType': 'bug', 'ResolvedBy': 'robertc'}, debug )
        test( dbc, "bugs robertc resolved since 2014/09/15", {'DateResolved': 'since20140915', 'ReportType': 'bug', 'ResolvedBy': 'robertc'}, debug )
        test( dbc, "bugs robertc resolved since 09/15/2014", {'DateResolved': 'since20140915', 'ReportType': 'bug', 'ResolvedBy': 'robertc'}, debug )
        test( dbc, "bugs robertc resolved since 9/15/14", {'DateResolved': 'since20140915', 'ReportType': 'bug', 'ResolvedBy': 'robertc'}, debug )
        test( dbc, "bugs robertc resolved since 9/15/98", {'DateResolved': 'since19980915', 'ReportType': 'bug', 'ResolvedBy': 'robertc'}, debug )
        test( dbc, "bugs robertc resolved since 1/15", {'DateResolved': 'since20150115', 'ReportType': 'bug', 'ResolvedBy': 'robertc'}, debug )
        test( dbc, "bugs robertc resolved since 12/5", {'DateResolved': 'since20141205', 'ReportType': 'bug', 'ResolvedBy': 'robertc'}, debug )
        test( dbc, "bugs robertc resolved from 12/15 to 1/5", {'DateResolved': 'from20141215to20150105', 'ReportType': 'bug', 'ResolvedBy': 'robertc'}, debug )

        test( dbc, "bugs reported before May 1 2013", {'DateReported': 'before20130501', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs reported till October", {'DateReported': 'before'+year_norm(10)+'1001', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs reported since Nov", {'DateReported': 'since'+year_norm(11)+'1101', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs reported from Nov, 2011", {'DateReported': 'since20111101', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs reported since last April", {'DateReported': 'since'+year_norm(4)+'0401', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs reported after May", {'DateReported': 'after'+year_norm(5)+'0531', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs reported after last Feb", {'DateReported': 'after'+year_norm(2)+'0228', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs reported in last Nov", {'DateReported': year_norm(11)+'1101-'+year_norm(11)+'1130', 'ReportType': 'bug'}, debug )
        test( dbc, "Mathematica bugs filed on 10th Oct", {'DateReported': '20141010', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "Mathematica bugs filed from 1st October to 15th October", {'DateReported': 'from20141001to20141015', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )

        # -- version inequalities
        test( dbc, "Mathematica bugs filed after 10.0.0.14", {'VersionReported': 'after10.0.0.14', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "Mathematica bugs reported since 10.0.0.14", {'VersionReported': 'since10.0.0.14', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "Mathematica bugs closed after V10", {'ResolutionVersion': 'after10', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "Mathematica bugs resolved up until V9", {'ResolutionVersion': 'upuntil9', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "Mathematica bugs resolved up to 9.1", {'ResolutionVersion': 'upto9.1', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "Mathematica bugs resolved since 10.0.1", {'ResolutionVersion': 'since10.0.1', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )

        test( dbc, "bugs iliang reported in >10.0.1", {'VersionReported': '>10.0.1', 'ReportedBy': 'iliang', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs resolved by iliang in <=10.0.1", {'ResolutionVersion': '<=10.0.1', 'ResolvedBy': 'iliang', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs closed in >=10.0.1 by iliang", {'ResolveTestedBy': 'iliang', 'ResolutionVersion': '>=10.0.1', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs filed in >=10.0.1 by iliang", {'ReportedBy': 'iliang', 'VersionReported': '>=10.0.1', 'ReportType': 'bug'}, debug )
        test( dbc, "Mathematica p1 open bugs resolved before 10.0.3 reported in or before 10.0.3", {'Status': 'open', 'VersionReported': 'inorbefore10.0.3', 'Priority': '1', 'Program': 'Mathematica', 'ReportType': 'bug', 'ResolutionVersion': 'before10.0.3'}, debug )

        test( dbc, "all Mathematica 10.0.1 p1 open bugs", {'Status': 'open', 'VersionReported': '10.0.1', 'Priority': '1', 'Program': 'Mathematica', 'ReportType': 'bug', 'Resolution': 'all'}, debug )
        test( dbc, "Open farea integrate", {'Status': 'Open', 'FunctionalArea': 'Integrate'}, debug )

        ## action in version
        test( dbc, "bugs danl resolved in V10", {'ResolutionVersion': '10', 'ReportType': 'bug', 'ResolvedBy': 'danl'}, debug )
        test( dbc, "Mathematica bugs resolved since 10.0.1", {'ResolutionVersion': 'since10.0.1', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs iliang reported since Aug 1", {'ReportedBy': 'iliang', 'DateReported': 'since20140801', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs iliang closed since version 10.0.1", {'ResolveTestedBy': 'iliang', 'ResolutionVersion': 'since10.0.1', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs closed by iliang since version 10.0.1", {'ResolveTestedBy': 'iliang', 'ResolutionVersion': 'since10.0.1', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs closed in V10 by iliang", {'ResolveTestedBy': 'iliang', 'ResolutionVersion': '10', 'ReportType': 'bug'}, debug )

        # -- bugs related to other reports
        test( dbc, "crm 1128937", {'SeeAlso': 'crm(1128937)'}, debug )
        test( dbc, "bugs with crm 1128937", {'ReportType': 'bug', 'SeeAlso': 'crm(1128937)'}, debug )
        test( dbc, "bugs related to crm 1128937", {'ReportType': 'bug', 'SeeAlso': 'crm(1128937)'}, debug )
        test( dbc, "bugs related to bug 127142",  {'ReportType': 'bug', 'SeeAlso': 'bug(127142),127142'}, debug )
        test( dbc, "bugs related to crm 1128937, 111111, and 2334 and status is open", {'status': 'open', 'ReportType': 'bug', 'SeeAlso': 'crm(1128937),crm(111111),crm(2334)'}, debug )
        test( dbc, "bugs related to bug 127142, 12345, and 123456", {'ReportType': 'bug', 'SeeAlso': 'bug(127142),bug(12345),bug(123456),127142,12345,123456'}, debug )
        test( dbc, "WolframAlpha CityData Duplicate related to bug 176538", {'FunctionalArea': 'CityData', 'Program': 'WolframAlpha', 'Resolution': 'Duplicate', 'SeeAlso': 'bug(176538),176538'}, debug )
        test( dbc, "WolframAlpha CityData Duplicate SeeAlso:176538", {'FunctionalArea': 'CityData', 'Program': 'WolframAlpha', 'Resolution': 'Duplicate', 'SeeAlso': '176538'}, debug )

        # -- M10 and fixed => Resolved Fixed
        test( dbc, "p1 open M10 bugs", {'Priority': '1', 'Status': 'open', 'VersionReported': '10', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "WolframAlpha bugs fixed in July", {'DateResolved': '20140701-20140731', 'ReportType': 'bug', 'Program': 'WolframAlpha', 'Resolution': 'Fixed'}, debug )
        test( dbc, "Integrate bugs fixed in V10.0.1", {'ReportType': 'bug', 'FunctionalArea': 'Integrate', 'ResolutionVersion': '10.0.1', 'Resolution': 'Fixed'}, debug )
        test( dbc, "Integrate bugs fixed in M10", {'ResolutionVersion': '10', 'FunctionalArea': 'Integrate', 'Program': 'Mathematica', 'Resolution': 'Fixed', 'ReportType': 'bug'}, debug )
        test( dbc, "p1,2 visualization bugs fixed in V10.0.1", {'Priority': '1,2', 'ReportType': 'bug', 'ResolutionVersion': '10.0.1', 'Resolution': 'Fixed', 'FunctionalCategory': 'Visualization'}, debug )

        test( dbc, "bugs resolved in version 10 as duplicate", {'ReportType': 'bug', 'ResolutionVersion': '10', 'Resolution': 'duplicate'}, debug )
        test( dbc, "bugs brettc resolved for 10.0.1", {'ResolutionVersion': '10.0.1', 'ReportType': 'bug', 'ResolvedBy': 'brettc'}, debug )
        test( dbc, "bugs brettc resolved on 10.0.1", {'ResolutionVersion': '10.0.1', 'ReportType': 'bug', 'ResolvedBy': 'brettc'}, debug )
        test( dbc, "bugs resolved by brettc in 10.0.1", {'ResolutionVersion': '10.0.1', 'ReportType': 'bug', 'ResolvedBy': 'brettc'}, debug )
        test( dbc, "bugs resolved by brettc for 10.0.1", {'ResolutionVersion': '10.0.1', 'ReportType': 'bug', 'ResolvedBy': 'brettc'}, debug )
        test( dbc, "bugs resolved as AsDesigned", {'ReportType': 'bug', 'Resolution': 'AsDesigned'}, debug )
        test( dbc, "Open integrate and nintegrate bugs", {'Status': 'Open', 'FunctionalArea': 'Integrate,NIntegrate', 'ReportType': 'bug'}, debug )
        test( dbc, "Mathematica and WolframDesktop open tag move requests TAG_MOVED", {'Status': 'open', 'Program': 'Mathematica,WolframDesktop', 'SeeAlso': 'TAGMOVE_REQUESTED,TAG_MOVED'}, debug )

        test( dbc, "p1 open frontend bugs", {'Priority': '1', 'Status': 'open', 'Component': 'Front-end', 'ReportType': 'bug'}, debug )
        test( dbc, "p1 open front end bugs", {'Priority': '1', 'Status': 'open', 'Component': 'Front-end', 'ReportType': 'bug'}, debug )
        test( dbc, "front end bugs reported in 10.0.1", {'ReportType': 'bug', 'VersionReported': '10.0.1', 'Component': 'Front-end'}, debug )
        test( dbc, "open wolfram finance platform fron tend bugs", {'Status': 'open', 'ReportType': 'bug', 'Program': 'wolframfinanceplatform', 'Component': 'frontend'}, debug )
        test( dbc, "open wfp front end bugs", {'Status': 'open', 'ReportType': 'bug', 'Program': 'WolframFinancePlatform', 'Component': 'FrontEnd'}, debug )

        test( dbc, "Mathematica open p1 bug reports", {'Status': 'open', 'Priority': '1', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "Mathematica open p1 crash reports", {'Status': 'open', 'Priority': '1', 'Program': 'Mathematica', 'ReportType': 'crash'}, debug )
        test( dbc, "Mathematica open p1 hangs", {'Status': 'open', 'Priority': '1', 'Program': 'Mathematica', 'ReportType': 'hang'}, debug )
        test( dbc, "Mathematica open p1 crashes", {'Status': 'open', 'Priority': '1', 'Program': 'Mathematica', 'ReportType': 'crash'}, debug )

        test( dbc, "body:+jump +process -- open bugs", {'Status': 'open', 'body': '+jump +process', 'ReportType': 'bug'}, debug )
        test( dbc, "body:[pw,cs,2000]jump -process -- open bugs", {'Status': 'open', 'body': '[pw,cs,2000]jump -process', 'ReportType': 'bug'}, debug )

        test( dbc, "open P0 Visualization bugs and suggestions", {'Status': 'open', 'Priority': '0', 'ReportType': 'bug,suggestion', 'FunctionalCategory': 'Visualization'}, debug )
        test( dbc, "bugs from carlosy", {'ReportedBy': 'carlosy', 'ReportType': 'bug'}, debug )
        test( dbc, "summary:~ D[*] from:carlosy suggestions", {'ReportedBy': 'carlosy', 'ReportType': 'suggestion', 'summary': '~D[*]'}, debug )

        # -- name mapping
        test( dbc, "player cloud fultz raj", {'FunctionalCategory': 'Cloud', 'PrimaryDeveloper': 'jfultz', 'Program': 'MathematicaPlayer', 'QAContact': 'rajb'}, debug )
        test( dbc, "Carlos's resolved bugs", {'Status': 'resolved', 'QAContact': 'carlosy', 'ReportType': 'bug'}, debug )
        test( dbc, "Shiral's resolved bugs", {'ReportedBy': 'shirald', 'Status': 'resolved', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs closed by Ilian last month", {'ReportType': 'bug', 'DateResolveTested': 'lastmonth', 'ResolveTestedBy': 'iliang'}, debug )

        test( dbc, 'WolframAlpha p1,2 subject contains "FirstName and GivenName"', {'Priority': '1,2', 'Program': 'WolframAlpha', 'summary': "'FirstName and GivenName'"}, debug )
        test( dbc, "WolframAlpha p1,2 subject containing 'FirstName and GivenName'", {'Priority': '1,2', 'Program': 'WolframAlpha', 'summary': "'FirstName and GivenName'"}, debug )
        test( dbc, 'WolframAlpha p1,2 header has "FirstName and GivenName"', {'Priority': '1,2', 'Program': 'WolframAlpha', 'summary': "'FirstName and GivenName'"}, debug )
        test( dbc, "WolframAlpha p1,2 header having 'FirstName and GivenName'", {'Priority': '1,2', 'Program': 'WolframAlpha', 'summary': "'FirstName and GivenName'"}, debug )
        test( dbc, "WolframAlpha body has GivenName", {'body': 'GivenName', 'Program': 'WolframAlpha'}, debug )
        test( dbc, "chiarab open bugs with seanc as QAContact", {'PrimaryDeveloper': 'chiarab', 'Status': 'open', 'QAContact': 'seanc', 'ReportType': 'bug'}, debug )

        # -- '=' and '!='
        test( dbc, "P1 open bugs Mathematica version reported = 10.0.2", {'Priority': '1', 'Status': 'open', 'versionreported': '10.0.2', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "P1 open bugs Mathematica reported version = 10.0.2", {'Priority': '1', 'Status': 'open', 'VersionReported': '10.0.2', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "P1 open bugs Mathematica reported version != 10.0.2", {'Priority': '1', 'Status': 'open', 'VersionReported': '!10.0.2', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "P1 open bugs Mathematica version reported =! 10.0.2", {'Priority': '1', 'Status': 'open', 'versionreported': '!10.0.2', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "P1 open bugs Mathematica reported in version 10.0.2", {'Priority': '1', 'Status': 'open', 'VersionReported': '10.0.2', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "P1 open bugs Mathematica reported version >= 10.0.2", {'Priority': '1', 'Status': 'open', 'VersionReported': '>=10.0.2', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )

        test( dbc, "P1 open bugs Mathematica version resolved=10.0.2", {'Priority': '1', 'Status': 'open', 'ResolutionVersion': '10.0.2', 'ReportType': 'bug', 'Program': 'Mathematica'}, debug )
        test( dbc, "P1 open bugs Mathematica resolution version=10.0.2", {'Priority': '1', 'Status': 'open', 'resolutionversion': '10.0.2', 'ReportType': 'bug', 'Program': 'Mathematica'}, debug )
        test( dbc, "P1 open bugs Mathematica version resolved!=10.0.2", {'Priority': '1', 'Status': 'open', 'ResolutionVersion': '!10.0.2', 'ReportType': 'bug', 'Program': 'Mathematica'}, debug )
        test( dbc, "P1 open bugs Mathematica version resolved=!10.0.2", {'Priority': '1', 'Status': 'open', 'ResolutionVersion': '!10.0.2', 'ReportType': 'bug', 'Program': 'Mathematica'}, debug )
        test( dbc, "P1 open bugs Mathematica resolved in version 10.0.2", {'Priority': '1', 'Status': 'open', 'ResolutionVersion': '10.0.2', 'ReportType': 'bug', 'Program': 'Mathematica'}, debug )
        test( dbc, "P1 open bugs Mathematica version resolved >= 10.0.2", {'Priority': '1', 'Status': 'open', 'ResolutionVersion': '>=10.0.2', 'ReportType': 'bug', 'Program': 'Mathematica'}, debug )

        test( dbc, "P1 open bugs Mathematica version reported <10.1.0 and version resolved <10.0.2", {'Status': 'open', 'versionreported': '<10.1.0', 'Priority': '1', 'Program': 'Mathematica', 'ReportType': 'bug', 'ResolutionVersion': '<10.0.2'}, debug )
        test( dbc, "P1 open bugs Mathematica reported version <10.1.0 and resolved version <10.0.2", {'Status': 'open', 'VersionReported': '<10.1.0', 'Priority': '1', 'Program': 'Mathematica', 'ReportType': 'bug', 'ResolutionVersion': '<10.0.2'}, debug )

        test( dbc, "Program=Mathematica Status = Open priority!=4,5", {'Status': 'Open', 'priority': '!4,5', 'Program': 'Mathematica'}, debug )
        test( dbc, "Program = WolframAlpha Open priority=1 bugs", {'Status': 'Open', 'priority': '1', 'Program': 'WolframAlpha', 'ReportType': 'bug'}, debug )

        # -- 10.x. etc..
        test( dbc, "P1 10.x open bugs", {'Priority': '1', 'Status': 'open', 'VersionReported': '10', 'ReportType': 'bug'}, debug )
        test( dbc, "P1 version 10.x open bugs", {'Priority': '1', 'Status': 'open', 'VersionReported': '10', 'ReportType': 'bug'}, debug )
        test( dbc, "P1 version reported 10.1.x open bugs", {'Priority': '1', 'Status': 'open', 'versionreported': '10.1', 'ReportType': 'bug'}, debug )

        # -- aliases
        test( dbc, "mma bugs filed today", {'DateReported': 'today', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "p1 M- bugs filed today", {'Priority': '1', 'DateReported': 'today', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "p1 Program : M- bugs filed today", {'Priority': '1', 'DateReported': 'today', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "p1 Program=M- bugs filed today", {'Priority': '1', 'DateReported': 'today', 'Program': 'Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "p1 Program = alpha, M- bugs filed today", {'Priority': '1', 'DateReported': 'today', 'Program': 'WolframAlpha,Mathematica', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs jfultz resolved lately", {'DateResolved': 'last30days', 'ReportType': 'bug', 'ResolvedBy': 'jfultz'}, debug );
        test( dbc, "my recently reported bugs", {'ReportedBy': 'bugs', 'DateReported': 'last30days', 'ReportType': 'bug'}, debug )
        test( dbc, "recently filed bugs", {'DateReported': 'last30days', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs iliang reported lately", {'ReportedBy': 'iliang', 'DateReported': 'last30days', 'ReportType': 'bug'}, debug )
        test( dbc, "brettc visualization bugs+", {'PrimaryDeveloper': 'brettc', 'FunctionalCategory': 'Visualization', 'ReportType': 'Bug,Suggestion'}, debug )
        test( dbc, "bugs+ of Mathematica", {'Program': 'Mathematica', 'ReportType': 'Bug,Suggestion'}, debug )
        test( dbc, "Mathematica open bugs+ filed today", {'Status': 'open', 'DateReported': 'today', 'Program': 'Mathematica', 'ReportType': 'Bug,Suggestion'}, debug )
        test( dbc, "Mathematica open reportedby:bugs+gosia filed today", {'ReportedBy': 'bugs+gosia', 'DateReported': 'today', 'Program': 'Mathematica', 'Status': 'open'}, debug )
        test( dbc, "features assigned to brettc", {'PrimaryDeveloper': 'brettc', 'ReportType': 'feature'}, debug )

        # -- bug fixes
        test( dbc, "WolframAlpha InventionData", {'FunctionalArea': 'InventionData', 'Program': 'WolframAlpha'}, debug )
        test( dbc, "P1 version reported >= 10 open bugs", {'Priority': '1', 'Status': 'open', 'versionreported': '>=10', 'ReportType': 'bug'}, debug )
        test( dbc, "P1 open bugs version reported 10", {'Priority': '1', 'Status': 'open', 'versionreported': '10', 'ReportType': 'bug'}, debug )
        test( dbc, "my open p0, p1, p2 bugs", {'ReportedBy': 'bugs', 'Status': 'open', 'Priority': '0,1,2', 'ReportType': 'bug'}, debug )
        test( dbc, "cboucher open bugs updated within last 28 days p3,p4,p5", {'PrimaryDeveloper': 'cboucher', 'Status': 'open', 'Priority': '3,4,5', 'ReportType': 'bug', 'LastUpdate': 'last28days'}, debug )
        test( dbc, "WolframCalculate SeeAlso ShowStopper status open or status resolved", {'status': 'open,resolved', 'Program': 'WolframCalculate', 'SeeAlso': 'ShowStopper'}, debug )
        test( dbc, "P1 open bugs Mathematica reported in 10.1.0 resolved in 10.0.2", {'Status': 'open', 'VersionReported': '10.1.0', 'Priority': '1', 'Program': 'Mathematica', 'ReportType': 'bug', 'ResolutionVersion': '10.0.2'}, debug )
        test( dbc, "P1 open bugs Mathematica reported <10.1.0 resolved >=10.0.2", {'Status': 'open', 'VersionReported': '<10.1.0', 'Priority': '1', 'Program': 'Mathematica', 'ReportType': 'bug', 'ResolutionVersion': '>=10.0.2'}, debug )
        test( dbc, "P1 open bugs Mathematica reported in <10.1.0 resolved in >=10.0.2", {'Status': 'open', 'VersionReported': '<10.1.0', 'Priority': '1', 'Program': 'Mathematica', 'ReportType': 'bug', 'ResolutionVersion': '>=10.0.2'}, debug )
        test( dbc, "P1 open bugs Mathematica version reported <10.1.0 resolved after 10.0.2", {'Status': 'open', 'versionreported': '<10.1.0', 'Priority': '1', 'Program': 'Mathematica', 'ReportType': 'bug', 'ResolutionVersion': 'after10.0.2'}, debug )

        # -- extension to do three part action parsing e.g. reported by dkapadia in 10.0.1 last 2 weeks
        test( dbc, "WolframAlpha Open bugs with developer: norikoy - johnnien updated since october 10 P4 P5", {'Status': 'Open', 'PrimaryDeveloper': 'norikoy - johnnien', 'LastUpdate': 'since20141010', 'Priority': '4,5', 'Program': 'WolframAlpha', 'ReportType': 'bug'}, debug )
        test( dbc, "P1 open bugs Mathematica resolution version <10.0.3 version reported >=10.0.0", {'Status': 'open', 'versionreported': '>=10.0.0', 'Priority': '1', 'Program': 'Mathematica', 'ReportType': 'bug', 'resolutionversion': '<10.0.3'}, debug )
        test( dbc, "Mathematica bugs resolved in 10.0.2 the last 3 days", {'DateResolved': 'last3days', 'ResolutionVersion': '10.0.2', 'ReportType': 'bug', 'Program': 'Mathematica'}, debug )
        test( dbc, "Mathematica bugs resolved between Jan 1 and Feb 15 by brettc before 10.0.2 p1 p2", {'DateResolved': 'between20150101and20150215', 'Priority': '1,2', 'Program': 'Mathematica', 'ReportType': 'bug', 'ResolutionVersion': 'before10.0.2', 'ResolvedBy': 'brettc'}, debug )
        test( dbc, "Mathematica bugs brettc resolved between Jan 1 and Feb 15 in or after 10.0.2 p1 p2", {'DateResolved': 'between20150101and20150215', 'Priority': '1,2', 'Program': 'Mathematica', 'ReportType': 'bug', 'ResolutionVersion': 'inorafter10.0.2', 'ResolvedBy': 'brettc'}, debug )
        test( dbc, "Mathematica bugs brettc resolved between Jan 1 and Feb 15 >=10.0.2 p1 p2", {'DateResolved': 'between20150101and20150215', 'Priority': '1,2', 'Program': 'Mathematica', 'ReportType': 'bug', 'ResolutionVersion': '>=10.0.2', 'ResolvedBy': 'brettc'}, debug )
        test( dbc, "Mathematica bugs brettc resolved between Jan 1 and Feb 15 in >=10.0.2 p1 p2", {'DateResolved': 'between20150101and20150215', 'Priority': '1,2', 'Program': 'Mathematica', 'ReportType': 'bug', 'ResolutionVersion': '>=10.0.2', 'ResolvedBy': 'brettc'}, debug )
        test( dbc, "Mathematica bugs reported by danl and rknapp last two weeks and resolved between Jan 1 and Feb 15 by brettc before 10.0.2 p1 p2", {'DateReported': 'last2weeks', 'ReportedBy': 'danl+rknapp', 'Priority': '1,2', 'DateResolved': 'between20150101and20150215', 'Program': 'Mathematica', 'ReportType': 'bug', 'ResolutionVersion': 'before10.0.2', 'ResolvedBy': 'brettc'}, debug )

        test( dbc, "not resolved yesterday p1 p2", {'DateResolved': '!yesterday', 'Priority': '1,2'}, debug )
        test( dbc, "reported today but not resolved yesterday p1 p2", {'DateResolved': '!yesterday', 'DateReported': 'today', 'Priority': '1,2'}, debug )
        test( dbc, "Mathematica bugs not resolved between Jan 1 and Feb 15 >=10.0.2 p1 p2", {'DateResolved': '!between20150101and20150215', 'Priority': '1,2', 'Program': 'Mathematica', 'ReportType': 'bug', 'ResolutionVersion': '>=10.0.2'}, debug )
        test( dbc, "Mathematica bugs reported by danl but not rknapp within last two weeks and resolved between Jan 1 and Feb 15 by brettc before 10.0.2 p1 p2", {'DateReported': 'last2weeks', 'ReportedBy': 'danl - rknapp', 'Priority': '1,2', 'DateResolved': 'between20150101and20150215', 'Program': 'Mathematica', 'ReportType': 'bug', 'ResolutionVersion': 'before10.0.2', 'ResolvedBy': 'brettc'}, debug )
        test( dbc, "Mathematica bugs not resolved by brettc from Jan 1 to Feb 15 >=10.0.2 p1 p2", {'DateResolved': 'from20150101to20150215', 'Priority': '1,2', 'Program': 'Mathematica', 'ReportType': 'bug', 'ResolutionVersion': '>=10.0.2', 'ResolvedBy': '!brettc'}, debug )

        # -- platform and branch related
        test( dbc, "Windows bugs", {'PlatformAffected': 'Windows', 'ReportType': 'bug'}, debug )
        test( dbc, "Linux bugs", {'PlatformAffected': 'Linux', 'ReportType': 'bug'}, debug )
        test( dbc, "32 bit Linux bugs", {'PlatformAffected': 'Linux-x86', 'ReportType': 'bug'}, debug )
        test( dbc, "32 bit linux bugs", {'PlatformAffected': 'Linux-x86', 'ReportType': 'bug'}, debug )
        test( dbc, "Linux-x86-64 bugs", {'PlatformAffected': 'Linux-x86-64', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs whose platform is Windows", {'PlatformAffected': 'Windows', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs whose platforms are Windows and Linux", {'PlatformAffected': 'Windows,Linux', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs whose platforms are windows and linux", {'PlatformAffected': 'windows,linux', 'ReportType': 'bug'}, debug )
        test( dbc, "broken on Windows and Linux", {'PlatformAffected': 'Windows,Linux', 'ReportType': 'bug'}, debug )
        test( dbc, "OSX bugs", {'PlatformAffected': 'MacOSX-x86-64', 'ReportType': 'bug' }, debug )
        test( dbc, "64 bit OSX bugs", {'PlatformAffected': 'MacOSX-x86-64', 'ReportType': 'bug' }, debug )
        test( dbc, "32 bit OSX bugs", {'PlatformAffected': 'MacOSX-x86', 'ReportType': 'bug' }, debug )
        test( dbc, "bugs on platforms Windows", {'PlatformAffected': 'Windows', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs whose platform affected is Windows", {'PlatformAffected': 'Windows', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs whose platform affected is 32 bit Windows", {'PlatformAffected': 'Windows-x86', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs fixed in TestBranch", {'ReportType': 'bug', 'Resolution': 'Fixed', 'Branch': 'TestBranch'}, debug )
        test( dbc, "Mathematica bugs whose branch is TestBranch", {'Program': 'Mathematica', 'ReportType': 'bug', 'branch': 'TestBranch'}, debug )
        test( dbc, "Mathematica bugs whose branch name is TestBranch", {'Program': 'Mathematica', 'ReportType': 'bug', 'Branch': 'TestBranch'}, debug )

        # -- more aliases
        test( dbc, "Wolfram System bugs whose branch name is TestBranch", {'Program': 'Mathematica', 'ReportType': 'bug', 'Branch': 'TestBranch'}, debug )
        test( dbc, "p1 wolframsystem open bugs", {'Priority':'1', 'Program': 'Mathematica', 'Status':'open', 'ReportType': 'bug'}, debug )
        test( dbc, "p1 WS open bugs", {'Priority':'1', 'Program': 'Mathematica', 'Status':'open', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs reported today on Wolfram System", {'ReportType': 'bug', 'DateReported':'today', 'Program': 'Mathematica' }, debug )
        test( dbc, "bugs reported today on WS", {'ReportType': 'bug', 'DateReported':'today', 'Program': 'Mathematica'}, debug )
        test( dbc, "ws bugs reported today", {'ReportType': 'bug', 'DateReported':'today', 'Program': 'Mathematica'}, debug )

        test( dbc, "Wolfram Language bugs whose branch name is TestBranch", {'Program': 'Mathematica', 'Component':'Kernel', 'ReportType': 'bug', 'Branch': 'TestBranch'}, debug )
        test( dbc, "p1 wolframlanguage open bugs", {'Priority':'1', 'Program': 'Mathematica', 'Component':'Kernel', 'Status':'open', 'ReportType': 'bug'}, debug )
        test( dbc, "p1 WL open bugs", {'Priority':'1', 'Program': 'Mathematica', 'Component':'Kernel', 'Status':'open', 'ReportType': 'bug'}, debug )
        test( dbc, "bugs reported today on Wolfram Language", {'ReportType': 'bug', 'DateReported':'today', 'Program': 'Mathematica', 'Component':'Kernel'}, debug )
        test( dbc, "bugs reported today on WL", {'ReportType': 'bug', 'DateReported':'today', 'Program': 'Mathematica', 'Component':'Kernel'}, debug )
        test( dbc, "wl bugs reported today", {'ReportType': 'bug', 'DateReported':'today', 'Program': 'Mathematica', 'Component':'Kernel'}, debug )

        # -- things we can't do at the moment
#       test( dbc, "WolframAlpha open bugs updated today by me", {}, debug )

        dbc.close()
    except KeyboardInterrupt:
        sys.exit(0)

