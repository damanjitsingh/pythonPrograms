#!/usr/local/bin/python

import os, sys, time, re, calendar, datetime, subprocess

from datetime import date

import MySQLdb
import MySQLdb.cursors

TesterDB   = { 'name':'testerdb',     'host':'testhub',      'user':'testmngr',   'password':'password'   }
TestDB     = { 'name':'testdb',       'host':'testhub',      'user':'testmngr',   'password':'password'   }
#ResultsDB  = { 'name':'resultsdb',    'host':'testhub',      'user':'testmngr',   'password':'password'   }
ResultsDB  = { 'name':'resultsdb',    'host':'testhub',      'user':'testmngr',   'password':'password'   }
ResultsDB2 = { 'name':'resultsdb',    'host':'testhub',     'user':'testmngr',   'password':'password'   }
Results    = { 'name':'results',      'host':'testhub',     'user':'testmngr',   'password':'password'   }
GcovDB     = { 'name':'gcov',         'host':'oldbugs',      'user':'mysql',      'password':'password'   }
NBTestDB   = { 'name':'nbt_dev',      'host':'nbtester',     'user':'nbt_master', 'password':'nbt_master' }
BuildDB    = { 'name':'buildhistory', 'host':'buildmonitor', 'user':'browse',     'password':''           }
BugStatsDB = { 'name':'statistics',   'host':'bugsdb',       'user':'mysql',      'password':'password'   }
BugStats   = { 'name':'bugstats',     'host':'bugsdb',       'user':'bugs',       'password':'password'   }

BugsTest     = { 'name':'test', 'host':'bugsdb',   'user':'bugs',     'password':'password' }
NBTesterTest = { 'name':'test', 'host':'nbtester', 'user':'testmngr', 'password':'password' }
TesthubTest  = { 'name':'test', 'host':'testhub',  'user':'testmngr', 'password':'password' }

AllDatabases = {'testerdb':TesterDB, 'testdb':TestDB, 'resultsdb':ResultsDB, 'resultsdb2':ResultsDB2, 'results':Results, 'gcovdb':GcovDB, 'nbt_dev':NBTestDB, 'buildhistory':BuildDB, 'statistics':BugStatsDB, 'bugstats':BugStats, 'bugs_test':BugsTest, 'nbtester_test':NBTesterTest, 'testhub_test':TesthubTest }


def GetDBC( db, opts={} ):
    """
    Returns a db connection (and newQ) with DictCursor. Set 'dict':False in opts to get a regular cursor.
    First argument should be a known database as defined in 'AllDatabases' (one of the keys). If the supplied 
    argument is already a database connection, it is returned with new=False (second value returned). If a new 
    connection was created, new is set to True
    """

    defaults = { 'dict':True } # -- dict=True => dictionary cursor
    for key in defaults.keys():
        if not opts.has_key( key ): opts[ key ] =  defaults[ key ]
    
    if type(db).__name__ == 'Connection':
        connection = db
        new = False
    else:
        try:
            db_par = AllDatabases[db]
            if opts['dict']:
                connection = MySQLdb.connect( host=db_par['host'], user=db_par['user'], passwd=db_par['password'], db=db_par['name'], cursorclass=MySQLdb.cursors.DictCursor )
            else:
                connection = MySQLdb.connect( host=db_par['host'], user=db_par['user'], passwd=db_par['password'], db=db_par['name'] )
            new = True
        except KeyError:
            print "***** Error: Unknown database '" + db + "'"
            raise

    return connection, new


def FetchRowsSimple( db, table, select='*', where=None, orderby=None, count=1000, start=0, dictQ=0 ):
    """
    Simple fetch row from a database
        count = 0: fetch all (no limit specification). Default limit is 1000'
        dictQ = 1: returns columns as a dictionary keyed by column name
    """
    if where: where_desc = 'where '+where
    else:     where_desc = ''

    if orderby: orderby_desc = 'order by ' + orderby
    else:       orderby_desc = ''

    if count: limit_desc = 'limit ' + str(start) + ',' + str(count)
    else    : limit_desc = ''

    query = "select %s from %s %s %s %s" % ( select, table, where_desc, orderby_desc, limit_desc )

    db     = AllDatabases[db]

    if dictQ: conn   = MySQLdb.connect( host=db['host'], user=db['user'], passwd=db['password'], db=db['name'], cursorclass=MySQLdb.cursors.DictCursor )
    else    : conn   = MySQLdb.connect( host=db['host'], user=db['user'], passwd=db['password'], db=db['name'] )

    cursor = conn.cursor()

    cursor.execute( query )
    rows = cursor.fetchall( )

    cursor.close()
    conn.close()

    return rows


def GetReferenceIDs( dbc, ref_table, names=[] ):
    """
    when a list of names is given, this returns the list of ids 
    from a reference table that has the columns id and name.
    """
    if not names: return []

    dbc, new_conQ = GetDBC( dbc )
    cursor = dbc.cursor()

    constr = "name in ('" + "','".join(names) + "')"
    cursor.execute( "select id from " + ref_table + " where " + constr )

    rows = cursor.fetchall()
    def ext(a): return a['id']
    ids = map( ext, rows )

    cursor.close()
    if new_conQ: dbc.close()

    return ids


def _permittedQ_bugs( dbc, area, flag, user, exclusiveQ ):
    """
    Check for permission in bugs area (on bugstats database)
    """
    dbc, new_conQ = GetDBC( dbc )
    cursor = dbc.cursor()

    if exclusiveQ: constr_perm = "area='%s'and flag='%s'" % ( area, flag )
    else:          constr_perm = "area in ('%s','all') and flag in ('%s','all')" % ( area, flag )

    query = "select count(*) as permission from permission where user='%s' and %s and status='enabled'" % ( user, constr_perm )
    cursor.execute( query )
    row = cursor.fetchone()

    cursor.close()
    if new_conQ: dbc.close()

    return row['permission']


def PermittedQ( dbc, main_area, sub_area=None, perm_flag=None, username=None, exclusiveQ=0 ):
    """
    Check for permission in bugs area (on bugstats database). 
    Entend when needed to cover tests area too
    exclusive: specific premissions required; 'all' is not allowed
    """
    if not  sub_area:  sub_area = 'all'
    if not perm_flag: perm_flag = 'all'

    if not username:
        try: username = os.environ['REMOTE_USER']
        except KeyError:
            try: username = os.environ['USER']
            except KeyError:
                try: username = os.environ['LOGNAME']
                except:
                    proc = subprocess.Popen( "whoami", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
                    proc_output, proc_error = proc.communicate()
                    output = proc_output.rstrip("\n\r")
                    username = output

    if not username:
        raise RuntimeError, "Cannot figure out the username"

    if main_area == 'bugs':
        return _permittedQ_bugs( dbc, sub_area, perm_flag, username, exclusiveQ )
    elif main_area == 'tests':
        raise RuntimeError, "Permissions checking in 'tests' not yet implemented"
    else:
        raise RuntimeError, "Main area ('bugs', 'tests', etc.) not defined."


def GetWeekBounds( weeks_skipped=0 ):
    """
    return the week bounds from Sunday to the following Saturday in yyyymmdd format.
    weeks_skipped specifies the number of weeks to skip back. 
    weeks_skipped = [0]: this week (last Sunday, next Saturday )
    weeks_skipped = 1  : last week (Sunday before last, last Saturday ) and so on
    """
    today = date.today().toordinal()

    last_sunday   = today - (today % 7)
    next_saturday = last_sunday + 6

    date_lower = last_sunday   - 7*weeks_skipped
    date_upper = next_saturday - 7*weeks_skipped

    week_range = ( date.fromordinal(date_lower).strftime("%Y%m%d"), date.fromordinal(date_upper).strftime("%Y%m%d") )

    return week_range


def GetLastWeekday( last_weekday ):
    """
    get the date in the form YYYYMMDD for last Sunday, Monday, etc.
    """
    weekday_digit = { 'monday':0, 'tuesday':1, 'wednesday':2, 'thursday':3, 'friday':4, 'saturday':5, 'sunday':6 }
    
    weekday_today     = datetime.datetime.today().weekday() # -- Monday:0
    weekday_reference = weekday_digit[ last_weekday.lower() ]

    diff = weekday_today - weekday_reference
    if diff <= 0: diff = 7 + diff

    today_ord    = date.today().toordinal()
    date_ref_ord = today_ord - diff

    date_last_weekday = date.fromordinal( date_ref_ord ).strftime("%Y%m%d")

    return date_last_weekday


def ParseDateConstraint( param, val ):
    """
    parse a date constraint specification
    "20120101"                     returns "param = '20120101'"
    "20120101, 20120201, 20120301" returns "param in ('20120101','20120201','20120301')"
    "form 20120101 to 20120201" or "20120101 - 20120201" returns "param >= '20120101' and param <= '20120201'"
    "between 20120101 and 20120201"                      returns "param >  '20120101' and param <  '20120201'"
    on | on or before | on or after | before | after | = | > | < | >= | <= | lt | le | gt | ge <date> returns  "param <oper> <date>" as appropriate
    a value that starts with '!' negates the selection
    """
    month_pattern = '(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
    month_name_to_num = dict((v.lower(),k) for k,v in enumerate(calendar.month_abbr)) # -- { 'january':'01', 'jan':'01', .... }
    month_name_to_num.update( dict((v.lower(),k) for k,v in enumerate(calendar.month_name)) )

    today     = time.strftime("%Y%m%d", time.localtime())
    yesterday = time.strftime("%Y%m%d", time.localtime(time.time() - 24*60*60))

    this_year  = time.strftime( "%Y", time.localtime() )
    last_year  = str( int(this_year) - 1 )
    this_month = time.strftime( "%m", time.localtime() )

    negateQ = re.search( '!', val )

    val_trimmed = re.sub(r'[!\'"\s_]*', '', val)
    val_trimmed = val_trimmed.lower()

    # -- replace today and yesterday with YYYYMMDD
    val_trimmed = val_trimmed.replace( 'today', today )
    val_trimmed = val_trimmed.replace( 'yesterday', yesterday )

    # -- replace [last] <weekday> with YYYYMMDD
    regexp_weekday = r'(?:last|)\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)'
    val_trimmed    = re.sub( regexp_weekday, lambda m: GetLastWeekday( m.group(1) ), val_trimmed )

    constr = None
    if re.match(r'^\d{8}$', val_trimmed):
        constr = param + " = '"  + val_trimmed + "'";
    elif re.match(r'^(\d{8},)*\d{8}$', val_trimmed):
        dates = val_trimmed.split(',')
        constr = param + ' in (' + ','.join( dates ) + ')'
    elif val_trimmed.startswith('from') or val_trimmed.startswith('since') or re.match(r'\d', val_trimmed) or val_trimmed.startswith('between'):
        oMatch1 = re.search( r'^\D*(\d{8})\D+(\d{8})\s*$', val_trimmed )
        oMatch2 = re.match(r'^(from|since)\s*(\d{8})', val_trimmed )
        if oMatch1:
            date_start, date_end = oMatch1.groups()
            if val_trimmed.startswith('between'):
                constr = param + " > '"  + date_start + "' and " + param + " < '"  + date_end + "'" 
            else:
                constr = param + " >= '" + date_start + "' and " + param + " <= '" + date_end + "'" 
        elif oMatch2:
            dummy, date = oMatch2.groups()
            constr = param + " >= '" + str( date ) + "'"
        else:
            raise "DateSpecificationError", "Invalid date constraint string (1) '" + val + "'"
    elif re.match(r'^(=|>|<|gt|lt|ge|le|on|after|before)', val_trimmed ):
        try:
            op_translate = { '=':'=', 'on':'=', '<':'<', 'before':'<', 'lt':'<', '<=':'<=', 'onorbefore':'<=', 'le':'<=', '>':'>', 'after':'>', 'gt':'>', '>=':'>=', 'onorafter':'>=', 'ge':'>=' }
            oMatch = re.search( r'^(\D+)(\d{8})\s*$', val_trimmed )
            op_specified, date = oMatch.groups()
            op_const = op_translate[ op_specified ]
            constr = param + ' ' + op_const + ' ' + "'"+date+"'" 
        except( KeyError, AttributeError ):
            raise "DateSpecificationError", "Invalid date constraint string (2)'" + val + "'"
    elif re.match( r'last\d+(day|week|month|year)s*', val_trimmed ): # -- last number of days/weeks/months/years
        oMatch = re.search( r'last(\d+)(day|week|month|year)s?\s*$', val_trimmed )
        num, unit = oMatch.groups()

        time_diff = int( num ) * 24 * 60 * 60
        if(   unit == 'week'  ): time_diff = time_diff * 7
        elif( unit == 'month' ): time_diff = time_diff * 30
        elif( unit == 'year'  ): time_diff = time_diff * 365
    
        then = time.strftime("%Y%m%d", time.localtime(time.time() - time_diff))
        constr = param + " >= '" + str( then ) + "'"
    elif re.match( r'(this|last)(week|month|year)', val_trimmed ): # -- this/last calendar month/year
        if val_trimmed == 'thisyear':
            date_min, date_max = today[:4]+'0101', today[:4]+'1231'
        elif val_trimmed == 'thismonth':
            date_min, date_max = today[:6]+'01', today[:6]+'31'
        elif val_trimmed == 'thisweek':
            date_min, date_max = GetWeekBounds( 0 )
            date_min, date_max = str(date_min), str(date_max)
        elif val_trimmed == 'lastyear':
            last_year = str( int( today[:4] ) - 1 )
            date_min, date_max = last_year+'0101', last_year+'1231'
        elif val_trimmed == 'lastmonth':
            last_month = int( today[4:6] ) - 1
            if   last_month == 0: last_month = str( int( today[:4] ) - 1 ) + '12'
            elif last_month < 10: last_month = today[:4] + '0' + str(last_month)
            else                : last_month = today[:4] +       str(last_month)
            date_min, date_max = last_month+'01', last_month+'31'
        elif val_trimmed == 'lastweek':
            date_min, date_max = GetWeekBounds( 1 )
            date_min, date_max = str(date_min), str(date_max)

        constr = param + " >= " + date_min + " and " + param + " <= " + date_max
    elif re.match( eval("r'(?i)(?:last|)"+month_pattern+"[,\s]*(\d{4}|)'"), val_trimmed ): # -- e.g. "Jaunuary[[,] 2014]" or "last January"
        m = re.match( eval("r'(?i)(?:last|)"+month_pattern+"[,\s]*(\d{4}|)'"), val_trimmed )
        month_name, year = m.groups()
        month_num = month_name_to_num[ month_name ]
        if not year:
            if int(this_month) > month_num: 
                year = this_year
            else:
                year = last_year

        year_month = "%s%02d" % ( year, month_num )
        date_min, date_max = year_month+'01', year_month+'31'
        constr = param + " >= " + date_min + " and " + param + " <= " + date_max
    else:
        raise "DateSpecificationError", "Invalid date constraint string (3)'" + val + "'"

    if negateQ: return 'not(' + constr + ')'
    else:       return constr


if __name__ == "__main__":
    """
     Just some tests for ParseDateConstraint(). Run the module on its own to run the tests
    """

    strs = []
    strs.append( [ '20120801', '20120601,20120701,20120801', 'today', 'yesterday', 'yesterday,today', 'before yesterday' ] )
    strs.append( [ 'on 20120801', 'on or before 20120801', 'on or after 20120801', 'before 20120801', 'after 20120801', 'from 20120801', 'since 20120801' ] )
    strs.append( [ 'this week', 'last week', 'this month', 'last month', 'this year', 'last year' ] )
    strs.append( [ '20120601-20120701', 'from 20120601 to 20120701', 'between 20120601 and 20120701' ] )
    strs.append( [ 'last 2 weeks', 'last 3 months', 'last 2 years' ] )
    strs.append( [ 'last Sunday', 'Sunday', 'since last Monday', 'since Monday', 'before last Tuesday', 'from last Wednesday', 'on last Thursday', 'on Thursday' ] )
    strs.append( [ 'Jan', 'January', 'Jan 2013', 'December', 'Dec 2010', 'Dec 2020'] )
    strs.append( [ 'last Jan', 'last January', 'lastJuly', 'last December' ] )

    for str_grp in strs:
        print ""
        for constr_str in str_grp:
            constr_sql = ParseDateConstraint( 'date', constr_str )
            print "%30s : %s" % ( constr_str, constr_sql )
