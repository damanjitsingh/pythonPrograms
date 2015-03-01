#!/usr/bin/python

# -- a module for bugs database work involving mostly mysql database.
# -- 2012-03-09: As of this date Bugs.Find and Bugs.Update have been added (along with many helper functions).
# --             These help search for bugs by parameter in mysql and update generally --shirald
# -- 2012-07-03: GetInfo, FindBugFile, MapAttrNames, SortAttrNames, and Sort have been added
#                See the function definition for the help message --shirald

import os, sys, re, time, subprocess, shlex
import General, Databases, Roots

AttrNames = {
    'in_column': ('bug_id','priority','magnitude','newbie_project','volunteer_project','pure_math_project','date_reported','date_resolved','date_resolve_tested','last_update','status','last_update'),
    'in_ref_general': ('product','report_type','resolution'),
    'in_ref_version': ('version_reported','resolution_version'),
    'in_index': ('summary','description','problem'),
    'multi_general': ('component','functional_category','functional_area','see_also','platform_affected','branch'),
    'multi_person': ('reported_by','primary_developer','project_manager','qa_contact','resolved_by','resolve_tested_by','review_completed_by'),
    'special': ('reopen','body')
    }


def IsEmptyValue( value, o_empty_val_match=None ):
    """
    check if the value is an empty value. When used in a loop, one may give the match object
    to speed up execution
    """

    if value is None: return True

    val = value.strip()
    if value == '': return True

    if o_empty_val_match is None:
        return  re.match( r'^(none|unset|undef|undefined|unknown|empty|unassigned|unclassified)$', val, re.IGNORECASE)
    else:
        return o_empty_val_match.match( val )


def MapEmptyValue( str ):
    """
    pretty much a convenient function to map empty values such as 'none', 'unassigned', 
    to an empty string which is how it's supposed to have been saved in the datbase
    """
    if str is None or str == "": return str

    if IsEmptyValue( str ): 
        return ""
    else: 
        return str


def _normalize_reopen( param_dic_mapped ):
    """
    This tries to normalize 'reopen' from paramerter dictionary that has mapped to the db param names.
    If the status is specified in such a way to include 'Open' bugs, 'reopen' is set to 'union' so
    if we take status in (<specified statuses>) or <to be reopened>. If not, 'reopen' is set to
    'intersection' where it will join with 'AND' like everything else 
    """
    try: 
        reopen = param_dic_mapped['reopen']
     
        if reopen == 1 or reopen == '1' or reopen == 'auto': # -- aut set
            try            : status = param_dic_mapped['status']
            except KeyError: status = ''

            if (re.search( 'Open', status, re.I ) and not re.search( '!', status )) or (not re.search( 'Open', status, re.I ) and re.search( '!', status )):
                reopen = 'union'
            else:
                reopen = 'intersection'
        elif reopen == 0 or reopen == '0' or reopen == 'ignore':
            reopen = ''

    except KeyError: 
        reopen = ''

    param_dic_mapped['reopen'] = reopen


def _fix_report_type( report_type ):
    """
    This resolves the report type specified in terms of "Bug" in such a way 
    that "Bug" is given as the intersection of not "Suggestion" and not "Feature"
    If all reports are intended '' is returned; if none, 'NONE' is retunred. This
    will hit no reports as there's no such report type
    """

    if report_type == '!': return 'NONE' # -- an odd case

    if not re.search( '(?i)Bug', report_type ): # -- no need to fix
        return report_type

    report_type = report_type.replace( 'bug', 'Bug' )
    report_type = report_type.replace( 'suggestion', 'Suggestion' )
    report_type = report_type.replace( 'feature', 'Feature' )

    univ = ('Bug', 'Suggestion', 'Feature')
    report_type_modified = report_type.replace( '!', '' )
    negateQ = report_type_modified != report_type

    rep_type_elems = report_type_modified.split(',')

    rep_type_elems_rest = list( set( univ ) - set( rep_type_elems ) )
    report_type_new_neg = ','.join( rep_type_elems_rest )

    if negateQ:
        if report_type_new_neg == '': return 'NONE'
        report_type_new = report_type_new_neg
    else:
        if report_type_new_neg == '': return ''
        report_type_new = '!' + report_type_new_neg

    return report_type_new


def _constr_for_in_table_value( param, val, univ=[] ):
    """
    Make constraint element for in table values in current_status.
    This is not intended for free text attributes (e.g. summary)
    """
    vals_arr, negateQ = General.csv_to_list( val )

    if not vals_arr: return None

    vals_arr.sort(); 
    univ_str = [ str(x) for x in univ ]; univ_str.sort()

    if vals_arr == univ_str: return 'true' # -- all possible values selected

    if negateQ: prep = ' not in '
    else      : prep = ' in '

    constr = param + prep + "('" + "','".join( vals_arr ) + "')"

    return constr


def _get_version_comp_ref_ids( dbc, op, val ):
    """
    get version table id values for version comparisons such as version_reported=10.0.1, 
    resolution_version=>=10. resolution_version=ge10.1, etc. Comparison is done up to
    4 digits: major, minor, release_num, and candidate. 10.1 means 10.1.any.any
    """
    if val is None: return [0]
    
    val = val.strip()
    if val == '': return [0]

    v = str( val ).split('.') # -- only specified digits;        e.g. 10.1
    V = []                    # -- all four digits (pad with 0s) e.g. 10.1.0.0

    if len(v) > 4:
        raise RuntimeError, "Version comparison is performed only up to the 4th digit"

    for i in range(4): # -- fill V with v and pad with 0 up to 4 elemets
       try:               V.append( v[i] )
       except IndexError: V.append( '0' )
    
    constr_eq, constr_lt, constr_gt = 'major=' + v[0], 'major<' + v[0], 'major>' + V[0]

    if len(v) > 1: 
        constr_eq += ' and minor=' + v[1]
        if v[1] != '0': constr_lt += ' or (major=' + v[0] + ' and minor<' + v[1] + ')'

    if len(v) > 2: 
        constr_eq += ' and release_num=' + v[2]
        if v[2] != '0': constr_lt += ' or (major=' + v[0] + ' and minor=' + v[1] + ' and release_num<' + v[2] + ')'

    if len(v) > 3: 
        constr_eq += ' and candidate=' + v[3]
        if v[3] != '0': constr_lt += ' or (major=' + v[0] + ' and minor=' + v[1] + ' and release_num=' + v[2] + ' and candidate<' + v[3] + ')'

    constr_gt += ' or (major=' + V[0] + ' and minor>' + V[1] + ')'
    constr_gt += ' or (major=' + V[0] + ' and minor=' + V[1] + ' and release_num>' + V[2] + ')'
    constr_gt += ' or (major=' + V[0] + ' and minor=' + V[1] + ' and release_num=' + V[2] + ' and candidate>' + V[3] + ')'

    op = op.replace(' ','').lower()
    if op in ( '==', '=', 'eq', 'in'):
        constr = '(' + constr_eq +')'
    elif op in ( '<', 'lt', 'before' ):
        constr = '(' + constr_lt + ')'
    elif op in ( '<=', 'le', 'inorbefore', 'upto', 'till', 'until', 'upuntil' ):
        constr = '((' + constr_eq +') or (' + constr_lt + '))'
    elif op in ( '>', 'gt', 'after' ):
        constr = '(' + constr_gt + ')'
    elif op in ( '>=', 'ge', 'inorafter', 'since', 'from' ):
        constr = '((' + constr_eq +') or (' + constr_gt + '))'
    else:
        raise RuntimeError, "Invalid version comparison operator"

    query = "select id from version where " + constr
    cur = dbc.cursor()
    cur.execute( query )
    rows = cur.fetchall()
    cur.close()

    def ext(a): return a['id']
    ver_ids = map( ext, rows )
        
    return ver_ids


def _constr_for_ref_table_value_single( dbc, param, val, ref_table=None ):
    """
    make constraint element for current_status columns that use reference tables.
    reference table name must be the same as the param
    """
    if ref_table is None: ref_table = param

    if param == 'product'     and val == 'WolframAlpha': val = 'WolframCalculate'
    if param == 'report_type': val = _fix_report_type( val )

    numeric_versionQ = False
    if ref_table == 'version': # -- identify version comparison operation
        oM = re.match( r'^(\D*)([\d\.,]+)$', val.strip() )
        if oM: # -- numeric version specified
            numeric_versionQ = True
            ver_comp_op, val = oM.groups()
            if ver_comp_op == '': ver_comp_op = '=='

    names_arr, negateQ = General.csv_to_list( val )
   
    if ref_table == 'version' and numeric_versionQ: 
        if ver_comp_op not in ('==','=','eq') and len(names_arr) > 1: # -- no inequality against multiple values
            raise RuntimeError, "Cannot check inequality against multiple version values"

        ids_arr = []
        for name in names_arr: # -- collect ids for each version.name value
            ids = _get_version_comp_ref_ids( dbc, ver_comp_op, name )
            ids_arr += ids
    else:
        ids_arr = map( str, Databases.GetReferenceIDs( dbc, ref_table, names_arr ) )

    if not ids_arr: ids_arr = [0]

    if negateQ: prep = ' not in '
    else      : prep = ' in '

    constr = param + '_id' + prep + "(" + ",".join( map(str, ids_arr) ) + ")"

    return constr


def _get_bugs_from_assign_table( dbc, param, vals_arr, negateQ=False, lower=None, upper=None, cur_stat_constr=None, bugs_list=None ):
    """
    _get_bugs_from_assign_table_core() behavior notes describe how this works for the most part. e.g. when QAContact=!stefanr is
    requested, those with QAContact=stefanr,iliang will apear, because the record relavant to iliang turns the condition to true 
    for the bugs. This layer only gets rid of such cases.
    """
    bnums_np = _get_bugs_from_assign_table_core( dbc, param, vals_arr, negateQ, lower, upper, cur_stat_constr, bugs_list )

    if negateQ:
        bnums_p = _get_bugs_from_assign_table_core( dbc, param, vals_arr, False, None, None, None, bnums_np )
        return list( set( bnums_np ) - set( bnums_p ) )
    else:
        return bnums_np


def _get_bugs_from_assign_table_core( dbc, param, vals_arr, negateQ=False, lower=None, upper=None, cur_stat_constr=None, bugs_list=None ):
    """
    Get the bugs assigned with a particular value of a multi value param (e.q. QAContact, FunctionalArea, etc).
    This assume a particular format of the database design (table names, column names, etc.); it's not a general function.
    e.g. assign table: 'qa_contact_assign' and has 'bugnumber' and 'person_id' column, 
      reference table: 'person' and has 'id' and 'name' columns

    If a pre-constructed constraint for current_status table is given current_status is joined and constraint is applied.
    If a list of bugs is given, only those from that list is looked at (bugnumber in (b1, b2,....))
    If negateQ == True: bugs whose param is not vals are returned (<param_assign_table> right join current_status is performed anyway)
    """
    if not vals_arr: return []
    if isinstance(bugs_list,(list,tuple)) and not bugs_list: return [] # -- empty bugs list in bugs constraint

    if param in AttrNames['multi_person']: ref_table = 'person'
    else                                 : ref_table = param

    vals_arr = map( MapEmptyValue, vals_arr )
    ids = Databases.GetReferenceIDs( dbc, ref_table, vals_arr )

    table_join, assign_table, assign_col = '', param + '_assign', ref_table + '_id'

    if ids:
        contr_ids_in  = assign_col + '     in (' + ','.join(map(str,ids)) + ')'
        contr_ids_out = assign_col + ' not in (' + ','.join(map(str,ids)) + ')'
    else:
        contr_ids_in  = 'false'
        contr_ids_out = 'true'

    if negateQ:
        constr = contr_ids_out
        if "" in vals_arr: # -- table: assign_tab left join current_status 
            table_join = 'left'
        else: # -- table: assign_tab right join current_status 
            constr = '(' + constr + ' or ' + assign_table + '.id is null)'
            table_join = 'right'
        constr_bug_col = 'bug_id' # -- if right joined with current_status, bug_id should be taken
    else:
        if "" in vals_arr: # -- table: assign_tab right join current_status 
            constr = '(' + contr_ids_in + ' or ' + assign_table + '.id is null)'
            table_join = 'right'
            constr_bug_col = 'bug_id' # -- if right joined with current_status, bug_id should be taken
        else: # -- table: assign_tab
            constr = contr_ids_in
            constr_bug_col = 'bugnumber'
            if cur_stat_constr: table_join = 'left'
   
    if table_join == 'left' or table_join == 'right': 
        table  = assign_table + ' ' + table_join + ' join current_status on current_status.bug_id=' + assign_table + '.bugnumber'
        column = 'current_status.bug_id as bugn'
    else:
        table  = assign_table
        column = 'bugnumber as bugn'

    if lower:     constr = constr + ' and ' + constr_bug_col + ' >= ' + str(lower)
    if upper:     constr = constr + ' and ' + constr_bug_col + ' <= ' + str(upper)
    if bugs_list: constr = constr + ' and ' + constr_bug_col + ' in (' + ','.join(map(str,bugs_list)) + ')'

    if cur_stat_constr:
        constr = constr + ' and ' + cur_stat_constr

    query  = 'select distinct ' + column + ' from ' + table + ' where ' + constr

    cursor = dbc.cursor()
    cursor.execute( query )

    rows = cursor.fetchall()
    def ext(a): return a['bugn']
    bugnumbers = map( ext, rows )

    return bugnumbers


def _modify_val_for_key( val ):
    """
    Some attribute values have invalid characters for keys. 
    This modifies it so it can be handle in a homogeneous way
    """
    val_mod = val.replace( '"', '__qq__' )
    val_mod = val_mod.replace( '/', '__slash__' )

    val_mod = val_mod.replace( '(', '__LPR__' )
    val_mod = val_mod.replace( ')', '__RPR__' )
    val_mod = val_mod.replace( '[', '__LBK__' )
    val_mod = val_mod.replace( ']', '__RBK__' )
    val_mod = val_mod.replace( '{', '__LBC__' )
    val_mod = val_mod.replace( '}', '__RBC__' )

    return val_mod


def _find_bugs_by_multi_value_param( dbc, param, val, lower=None, upper=None, cur_stat_constr=None, bugs_list=None ):
    """
    This gets bugs by parameter values that can take multiple values. e.q. FuncationalArea: FA1, FA2, FA3...
    Multiple value elements in val can be connected with the set operations & (intersection), | (union), and - (complement)
    Character maps '+'=>'&', ','=>'|', '!'=>'-', '__and__'=>'&', '__or__'=>'|', '__not__'=>'-' are made. 
    Other characters are removed and multiple adjacent ops are replaced with the leading one ('&|' => '&'). 
    These are done in order not have to make it complicated.
    valid expressions: v1 & v2 - v3 => v1 and v2 but not v3
                       v1 + v2      => v1 or  v2 

    If a pre-constructed constraint for current_status table is given current_status is joined and constraint is applied.
    If a list of bugs is give, only those from that list is looked at (bugnumber in (b1, b2,....))
    """
    if isinstance(bugs_list,(list,tuple)) and not bugs_list: return [] # -- empty bugs list in bugs constraint

#   val_valid = re.sub( r'[^\w\s,&+\|\-!_/\."]', '', val )  # -- remove invalid characters. Some FuncArea values and double quotes
    val_valid = re.sub( r'[^\w\s,&+\|\-!_/\."()\[\]]', '', val )  # -- remove invalid characters. Some FuncArea values and double quotes

#   val_valid = re.sub( '\s*([,&+\|\-!])[\s,&+\|\-!]*', r' \1 ', val_valid ) # -- replace multi ops with the leading one (e.g. &| => &)
                                                                             # -- this fails when we have to allow mid word '-'. e.g. Front-end

    val_valid = re.sub( '([,&+\|!])', r' \1 ', val_valid ) # -- put a space around every sign but '-'
    val_valid = re.sub( r'\b\-\s', r' ', val_valid ) # -- replace dangling '-' to the right
    val_valid = re.sub( r'\s\-\b', r' ', val_valid ) # -- replace danglinh '-' to the left
    val_valid = re.sub( '\s+([,&+\|\-!])[\s,&+\|\-!]*', r' \1 ', val_valid ) # -- replace space + multi ops with the leading op (e.g. &| => &)

    val_expr = val_valid

    val_expr  = val_expr.replace( ',', '|' ) # -- replace alternative char with the language specific
    val_expr  = val_expr.replace( '+', '&' ) # -- and get rid of the leading and trailing ops
    val_expr  = val_expr.replace( '!', '-' ) 

    val_expr  = val_expr.replace( '__and__', ' & ' ) 
    val_expr  = val_expr.replace( '__or__',  ' | ' )
    val_expr  = val_expr.replace( '__not__', ' - ' )

#   if re.search( r'\s*\-', val_expr ): negateQ = True # -- note that this check only for leading '-': negated list
#   else:                               negateQ = False

    if re.match( r'\s*\-', val_expr ): negateQ = True # -- note that this checks only for leading '-': negated list
    else:                              negateQ = False

    val_expr  = val_expr.strip( ',&|- ' )    # -- space must be included among the chars within quotes

    val_items_cs = re.sub( '\s+[&+\|\-!]\s+', ',', val_expr ) # -- comma separated list to get bug numbers

    vals_arr, dummy = General.csv_to_list( val_items_cs )

#   if re.match(r'^[\w\s\|]+$', val_expr): # -- if a simple list of vals (e.g. danl,adams or !danl,adams), do in one call 
#       return _get_bugs_from_assign_table( dbc, param, vals_arr, negateQ, lower, upper, cur_stat_constr, bugs_list )

    # -- if a simple list of vals (e.g. danl,adams or !danl,adams), do in one call.
    # -- only '-'s not surrounded by spaces (e.g. Front-end) are allowed
#   if re.match(r'^[\w\s\|\s-]+$', val_expr) and not re.search(r'\s\-\s', val_expr): 
    if re.match(r'^[\w\s\|\s\-\.()\[\]]+$', val_expr) and not re.search(r'\s\-\s', val_expr): 
        return _get_bugs_from_assign_table( dbc, param, vals_arr, negateQ, lower, upper, cur_stat_constr, bugs_list )

    bugs_by_val = {}; bugs = []
    for val in vals_arr:
        val_key = _modify_val_for_key( val )
        bugs_by_val[val_key] = _get_bugs_from_assign_table( dbc, param, [ val ], False, lower, upper, cur_stat_constr, bugs_list )

    if val_expr == '': # -- if empty string ('strip' reduces space only string to empty string), only bugs with no value set to this param are sought
        bugs = bugs_by_val['']
    else:
        val_expr_mod = _modify_val_for_key( val_expr )
        val_eval     = re.sub( r'\b([\w\-\.]+)\b', r'set(bugs_by_val["\1"])', val_expr_mod )

        bugs = list( eval( val_eval ) )

    return bugs


# -- These functions constructs the constraint for the relevant parameter
def             _bugid( val, *rest ): return _constr_for_in_table_value( 'current_status.bug_id',            val )
def          _priority( val, *rest ): return _constr_for_in_table_value( 'current_status.priority',          val, [0,1,2,3,4,5] )
def         _magnitude( val, *rest ): return _constr_for_in_table_value( 'current_status.magnitude',         val, [0,1,2,3,4,5] )
def    _newbie_project( val, *rest ): return _constr_for_in_table_value( 'current_status.newbie_project',    val, [0,1] )
def _volunteer_project( val, *rest ): return _constr_for_in_table_value( 'current_status.volunteer_project', val, [0,1] )
def _pure_math_project( val, *rest ): return _constr_for_in_table_value( 'current_status.pure_math_project', val, [0,1] )
def            _status( val, *rest ): return _constr_for_in_table_value( 'current_status.status',            val, ['Open','Resolved','Closed'] )

def    _newbieproject( val, *rest ): return _newbie_project( val, rest ) 
def _volunteerproject( val, *rest ): return _volunteer_project( val, rest )
def  _puremathproject( val, *rest ): return _pure_math_project( val, rest )

def       _date_reported( val, *rest ): return Databases.ParseDateConstraint( 'date_reported',       val )
def       _date_resolved( val, *rest ): return Databases.ParseDateConstraint( 'date_resolved',       val )
def _date_resolve_tested( val, *rest ): return Databases.ParseDateConstraint( 'date_resolve_tested', val )
def         _last_update( val, *rest ): return Databases.ParseDateConstraint( 'date(last_update)',   val )

def _datereported( val, *rest ): return _date_reported( val, rest )
def _dateresolved( val, *rest ): return _date_resolved( val, rest )

def            _product( val, dbc, *rest ): return _constr_for_ref_table_value_single( dbc, 'product', val )
def        _report_type( val, dbc, *rest ): return _constr_for_ref_table_value_single( dbc, 'report_type', val )
def   _version_reported( val, dbc, *rest ): return _constr_for_ref_table_value_single( dbc, 'version_reported', val, 'version' )
def _resolution_version( val, dbc, *rest ): return _constr_for_ref_table_value_single( dbc, 'resolution_version', val, 'version' )
def         _resolution( val, dbc, *rest ): return _constr_for_ref_table_value_single( dbc, 'resolution', val )

def        _reporttype( val, dbc, *rest ): return _report_type( val, dbc, rest )
def   _versionreported( val, dbc, *rest ): return _version_reported( val, dbc, rest )
def _resolutionversion( val, dbc, *rest ): return _resolution_version( val, dbc, rest )

# -- These functions straight away fetch bug numbers from multi value assign tables
# -- These will probably be OBSOLETE 2013-01-22
def           _component( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None ):
    return _find_bugs_by_multi_value_param( dbc, 'component', val, lower, upper, cur_stat_constr, bugs_list )

def     _functional_area( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None ):
    return _find_bugs_by_multi_value_param( dbc, 'functional_area', val, lower, upper, cur_stat_constr, bugs_list )

def _functional_category( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None ):
    return _find_bugs_by_multi_value_param( dbc, 'functional_category', val, lower, upper, cur_stat_constr, bugs_list )

def     _project_manager( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None ):
    return _find_bugs_by_multi_value_param( dbc, 'project_manager', val, lower, upper, cur_stat_constr, bugs_list )

def   _primary_developer( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None ):
    return _find_bugs_by_multi_value_param( dbc, 'primary_developer', val, lower, upper, cur_stat_constr, bugs_list )

def          _qa_contact( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None ):
    return _find_bugs_by_multi_value_param( dbc, 'qa_contact', val, lower, upper, cur_stat_constr, bugs_list )

def         _reported_by( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None ):
    return _find_bugs_by_multi_value_param( dbc, 'reported_by', val, lower, upper, cur_stat_constr, bugs_list )

def   _resolve_tested_by( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None):
    return _find_bugs_by_multi_value_param( dbc, 'resolve_tested_by', val, lower, upper, cur_stat_constr, bugs_list )

def         _resolved_by( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None ):
    return _find_bugs_by_multi_value_param( dbc, 'resolved_by', val, lower, upper, cur_stat_constr, bugs_list )

def _review_completed_by( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None ):
    return _find_bugs_by_multi_value_param( dbc, 'review_completed_by', val, lower, upper, cur_stat_constr, bugs_list )

def            _see_also( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None ):
    return _find_bugs_by_multi_value_param( dbc, 'see_also', val, lower, upper, cur_stat_constr, bugs_list )

def     _functionalarea( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None ): return _functional_area( val, dbc, lower, upper, cur_stat_constr, bugs_list )
def _functionalcategory( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None ): return _functional_category( val, dbc, lower, upper, cur_stat_constr, bugs_list )
def     _projectmanager( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None ): return _project_manager( val, dbc, lower, upper, cur_stat_constr, bugs_list )
def   _primarydeveloper( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None ): return _primary_developer( val, dbc, lower, upper, cur_stat_constr, bugs_list )
def          _qacontact( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None ): return _qa_contact( val, dbc, lower, upper, cur_stat_constr, bugs_list )
def         _reportedby( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None ): return _reported_by( val, dbc, lower, upper, cur_stat_constr, bugs_list )
def    _resolvetestedby( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None ): return _resolve_tested_by( val, dbc, lower, upper, cur_stat_constr, bugs_list )
def         _resolvedby( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None ): return _resolved_by( val, dbc, lower, upper, cur_stat_constr, bugs_list )
def  _reviewcompletedby( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None ): return _review_completed_by( val, dbc, lower, upper, cur_stat_constr, bugs_list )
def            _seealso( val, dbc, lower, upper, cur_stat_constr=None, bugs_list=None ): return _see_also( val, dbc, lower, upper, cur_stat_constr, bugs_list )


def _get_reopen_constr():
    """
    make part of the constraint that picks bugs set to be reopened when joined with current_status (for union with status)
    """
    today  = time.strftime("%Y%m%d", time.localtime()) # -- get to be Opend
    constr = "see_also.name like 'REOPEN\_20%' and see_also.name >= 'REOPEN_" + today + "' and see_also_assign.status='current'"

    return constr


def _get_bugs_to_be_reopened( dbc, lower=None, upper=None, cur_stat_constr=None, bugs_list=None ):
    """
    get bugs to be reopened: SeeAlso has REOPEN_<date>. 
    """
    if isinstance(bugs_list,(list,tuple)) and not bugs_list: return [] # -- empty bugs list in bugs constraint

    table  = 'see_also_assign left join see_also on see_also_assign.see_also_id=see_also.id'
    constr = _get_reopen_constr() # -- bugs to be reopened

    if lower: constr = constr + ' and bugnumber >= ' + str(lower)
    if upper: constr = constr + ' and bugnumber <= ' + str(upper)

    if bugs_list: # -- empty list is taken care of at the top
        constr = constr + ' and bugnumber in (' + ','.join(map(str,bugs_list)) + ')'

    if cur_stat_constr:
        table  = '(' + table + ') left join current_status on current_status.bug_id=see_also_assign.bugnumber'
        constr = constr + ' and ' + cur_stat_constr

    query  = 'select distinct bugnumber from ' + table + ' where ' + constr
   
    cursor = dbc.cursor()
    cursor.execute( query )

    rows = cursor.fetchall()
    def ext(a): return a['bugnumber']
    bugs = map( ext, rows )

    cursor.close()

    return bugs


def _reopen( val, dbc, lower=None, upper=None, cur_stat_constr=None, bugs_list=None ):
    # -- val is here only to be compatible with the rest when in a loop; otherwise not used.
    # -- It comes in as a string with boole converted to int. So check for '0'
    # -- Do not return an empty string (empty === no match)
    # -- This will probably be OBSOLETE -- 2013-01-22
    if not val or val == '0': return None 
    return _get_bugs_to_be_reopened( dbc, lower, upper, cur_stat_constr, bugs_list )


def _get_bugs_from_current_status_tab( dbc, constr_single, join_see_also=False, lower=None, upper=None, bugs_list=None ):
    """
    given the constraint elements, returns bug numbers from current_status table.
    see_also needs to be joined when 'reopen' is also used.
    """
    if isinstance(bugs_list,(list,tuple)) and not bugs_list: return [] # -- empty bugs list in bugs constraint

    if join_see_also:
        table = '(current_status left join see_also_assign on current_status.bug_id=see_also_assign.bugnumber) left join see_also on see_also_assign.see_also_id=see_also.id'
    else:
        table = 'current_status'

    constr_elems = [ constr_single ]
    if lower: constr_elems.append( 'bug_id >= ' + str(lower) )
    if upper: constr_elems.append( 'bug_id <= ' + str(upper) )
    if bugs_list: constr_elems.append( 'bug_id in (' + ','.join(map(str,bugs_list)) + ')' )

    if not constr_elems: return None # -- not an empty list which is the same as no match

    constraint = ' and '.join( constr_elems )

    query = 'select distinct current_status.bug_id as bugnumber from ' + table + ' where ' + constraint
    cursor = dbc.cursor()
    cursor.execute( query )

    rows = cursor.fetchall()
    def ext(a): return a['bugnumber']
    bugs = map( ext, rows )

    cursor.close()

    return bugs


def MapAttrNames( attributes, output='csv' ): 
    """
    Fix mutiple stray spaces and commas and map multiple forms of attribute names to the form 
    that the database uses. e.g. QAContact, qa_contact, qacontact, etc... all return qa_contact.
    If a mapping is not defined here, that string is returned in tact (e.g. resolution, bugnumber)
    """
    attr_map = {}
    for type, a_list in AttrNames.iteritems():
        for attr in a_list: # -- prepare the mapping dictionary
            attr_norm = attr.replace('_','').lower()
            attr_map[attr_norm] = attr

    if isinstance( attributes, list ) or isinstance( attributes, tuple ): 
        attributes = ','.join(attributes)

    attr_norm_str = attributes.replace('_','').lower()
    attr_norm_str = re.sub( r'program', 'product', attr_norm_str )              # -- program is product in the database
    attr_norm_str = re.sub( r'^platform$', 'platformaffected', attr_norm_str )  # -- platform is mapped to platform_affected
    attr_norm_str = re.sub( r'dateclosed', 'dateresolvetested', attr_norm_str ) # -- date_closed => date_resolve_tested
    attr_norm_str = re.sub( r'lastupdated', 'lastupdate', attr_norm_str )       # -- last_updated => last_update
    attr_norm_str = attr_norm_str.strip(', ') # -- strip leading and tailing spaces and commas

    attr_norm_list = re.split( r'[\s,]*,[\s,]*', attr_norm_str ) 
    attr_norm_list = General.unique( attr_norm_list )

    attr_list = []
    for attr in attr_norm_list: # map to the db names
        if attr in attr_map:
            attr_list.append( attr_map[attr] ) 
        else:
            attr_list.append( attr ) 

    if output == 'list':
        return attr_list
    else:
        return ','.join( attr_list )


def SortAttrNames( attr_list ):
    """
    Sort attributes in to a dictionary of lists according the way they are stored in the database: 
    Make sure attribute names have been fixed using MapAttrNames() before feeding into this funcion.

         in_column: value is in current_status table (e.g. status)
    in_ref_general: general single value in reference table and its row id in current_status (e.g. resolution)
    in_ref_version: single version value in version table and its row id in current_status (e.g. resolution_version)
     multi_general: general multi value attribute in attr and attr_assign tables (e.g. functional_area)
      multi_person: personal mutil value attribute in person and attr_assign tables (e.g. qa_contact)

    This has only what's in the database. So, it doesn't handle bug_id => bugnumber conversion.
    """
    attr_name_to_type = {}
    for type, a_list in AttrNames.iteritems(): # -- reverse map
        for attr in a_list: attr_name_to_type[ attr ] = type

    if isinstance( attr_list, basestring ) and attr_list: # -- make a list if a string is given
        attr_list = re.split( r'[\s,]*,[\s,]*', attr_list )

    attr_sorted = {}
    for attr in attr_list: # -- sort
        try:
            type = attr_name_to_type[ attr ]
        except KeyError: 
            raise "InvalidBugAttributeError", "Don't know how to sort by attribute '" + attr + "'."

        if type not in attr_sorted: 
            attr_sorted[ type ] = []

        attr_sorted[ type ].append( attr )

    return attr_sorted


def _get_query_elems_for_sorting( sortby_list ):
    """
    Joins the talbles for sorting by single value attributes
    """
    table, sortby_list_mod = 'bug_nums_temp left join current_status using(bug_id)', []

    sortby_dict = SortAttrNames( sortby_list )

    for attr in sortby_list:
        if attr in sortby_dict['in_column']:
            sortby_list_mod.append( attr )
        elif 'in_ref_general' in sortby_dict and attr in sortby_dict['in_ref_general']: 
            table = '(' + table + ')' + ' left join ' + attr + ' on current_status' + '.' + attr + '_id=' + attr + '.id'
            sortby_list_mod.append( attr + '.name' )
        elif 'in_ref_version' in sortby_dict and attr in sortby_dict['in_ref_version']: 
            table = '(' + table + ')' + ' left join version as ' + attr + ' on current_status' + '.' + attr + '_id=' + attr + '.id'
            sortby_list_mod.append( attr + '.name' )
        else:
            raise "InvalidBugAttributeError", "Cannot sort by attribute '" + attr + "'."
            
    sortby_str = ','.join( sortby_list_mod )

    return table, sortby_str


def Sort( bugnums, sortby='bugnumber', db='bugstats' ):
    """
    Sort a list of bug number by single valued attributes
    """
    sortby = re.sub( r'(bugnumber|bugid)', 'bug_id', sortby ) # -- bug_id is the columns in current_status

    if sortby == 'bug_id':
        return sorted( bugnums )

    sortby_list = MapAttrNames( sortby, 'list')
    joined_table, sortby_str = _get_query_elems_for_sorting( sortby_list )

    dbc, newQ = Databases.GetDBC( db );

    cursor = dbc.cursor()
    cursor.execute("create temporary table bug_nums_temp( bug_id int unsigned not null default 0 )")
    cursor.executemany("insert into bug_nums_temp (bug_id) values(%s)", bugnums )

    query = "select bug_nums_temp.bug_id from "+joined_table+" order by " + sortby_str;
    cursor.execute( query )
    
    rows = cursor.fetchall()
    def ext(a): return a['bug_id']
    bugnums_sorted = map( ext, rows )

    if newQ: dbc.close()

    return bugnums_sorted


def _to_glimpse_syntax( q_str ): # -- might become OBSOLETE
    """
    This is used for full text body keyword search using glimpse.
    In order to maintain some resemblance to mysql full-text search syntax, 
    this does a very simple transformation that works only for simple queries
    that use logical operators and parentheses.
    Replacements: ' '=>',' (OR), '+'=>';' (AND), '-'=>';~' (AND NOT), '(':'{', ')':'}'
    Phrases within single or double quotes are spared. 
    """
    q_str = re.sub( r'\s+', ' ', q_str.strip() ) # -- multi-space => single space
    q_str = re.sub( r'(\S)\-(\S)', r'\1__HYPHEN__\2', q_str ) # -- preserve hyphen surrounded by non-spaces
    q_str = re.sub( r"(\w)'(\w)", r"\1\\'2", q_str ) # -- escape apostrophe. For some reason shlex.split() chokes on e.g. "jack's name"

    tokens = shlex.split( q_str ) # -- tokenize (quoted phrases become a single token)

    phraseM, phrase_num, phrases = re.compile( r'[\'"\s]' ), 1, {}
    for i in range( len(tokens) ): # -- separate phrasal tokens with a key for processing
        if phraseM.search( tokens[i] ):
            key = '__PHRASE'+str(i)+'__'
            phrases[key] = tokens[i]
            tokens[i]    = key

    q_str = ' '.join( tokens ) # -- new query with key tokens in pace of phrasal tokens
    q_str = re.sub( r'\s*([\+\-])\s*', r'\1', q_str ) # -- get rid of the spaces around + and - now

    op_g = { ' ':',', '+':';', '-':';~', '(':'{', ')':'}' }  # -- mysql => glimpse: OR, AND, and NOT (NOT => AND NOT), ()

    q_str_g = ''
    for c in q_str: # -- run through the new query replace mysql logical ops
        if c in op_g:  # -- substitute if translation defined
            c = op_g[c]
        q_str_g += c

    for key,val in phrases.iteritems(): # -- put the phrasal tokens in
        q_str_g = q_str_g.replace( key, repr(val) )

    q_str_g = q_str_g.replace('__HYPHEN__', '-').strip(' ;') # -- put the '-'s in

    return q_str_g


def _get_bugs_from_glimpse( query ):
    """
    Do a keyword search on the full data file body and returns the list of bugs. 
    This does a simple syntax transformation from WRI preferred or MySQL form
    to Glimpse form; see _translate_to_boolean().
    """
    query = query.strip()

    opts = { 'pw':0, 'cs':0, 'count':1000 } # -- get whole-words, and case-sensitive options
    opt_regexp = r'^(?i)\[([pwcsi\d,\s]*)\]'
    oM = re.search( opt_regexp, query )

    if oM: 
        opts_arr = oM.group(1).replace(' ','').split(',')
        for o in opts_arr: 
            if o.isdigit(): opts['count'] = int(o)
            else:           opts[o.lower()] = 1
        query = re.sub( opt_regexp, '', query )

    if opts['count'] > 5000: opts['count'] = 5000 # -- limit minimum at 5000

    query = _translate_to_boolean( query, mode="glimpse" )
  
    # -- -W: process whole files (not lines); -y: no prompt; take 'yes' for all, -L: limit hits, -l: don't show hit lines
    # -- -F: match pattern in file path; i.e. skip /backup/ and /new/ files.
    # --     These are skipped when indexing (/backup/ and /new/ in Build/.glimpse_exclude)
    # --     Here we are just being safe.
    glimpse_cmd    = "/usr/local/bin/glimpse -W -y -L 0:"+str(opts['count'])+" -l -F '/[0-9][0-9]*/[0-9][0-9]*/[0-9][0-9]*'"
    if not opts['pw']: glimpse_cmd += ' -w' # -- match only whole words
    if not opts['cs']: glimpse_cmd += ' -i' # -- case insensitive
    glimpse_cmd += ' -H '+Roots.BugsGlimpseRoot+'/IndexFiles/Live' # -- glimpse index location
    if re.match( r'^[\'"].+[\'"]$', query ): # -- don't requote if already within quotes
        glimpse_cmd += " "+query
    else:
        glimpse_cmd += " "+repr(query)
#   print >> sys.stderr, glimpse_cmd, '::'.join(shlex.split(glimpse_cmd ))

    bug_nums = []
    process = subprocess.Popen( shlex.split( glimpse_cmd ), stdout=subprocess.PIPE )
    for l in process.stdout:
        l = l.strip()
        path_elems = l.split('/')
        if path_elems[-1].isdigit():
            bug_nums.append( path_elems[-1] )
    
    return bug_nums


def _adjust_pattern( pat ):
    """
    do a simple adjustment (complicated patterns will break this) 
    from common wild cards '*' and '.' to mysql '%' and '_'
    """
    if not pat: return pat

    pat = pat.replace('%', '\%' )
    pat = pat.replace('_', '\_' )

    pat = re.sub( r'(?<=[^\\])\*', '%', pat )
    pat = re.sub( r'(?<=[^\\])\.', '_', pat )

    pat = pat.replace('\*', '*' )
    pat = pat.replace('\.', '.' )

    return pat


def _translate_to_boolean( val, mode="mysql" ):
    """
    This translates a full text search query string to roughly from WRI 
    (Arnoud & Raj) preferred way to either MySQL full text boolean form
    (a.g. Implied Boolean Logic) or Glimpse form. This is rough in the 
    sense that we try to convert only simple queries that has AND, OR
    and NOT logical operators.
    """
    if not val: return val
    val = val.strip()

    # -- for convenience, if one wants to easily edit a URL
    val = re.sub( r'__(pos|positive|plus|and)__',  ' +', val )
    val = re.sub( r'__(neg|negative|minus|not)__', ' -', val )
    val = val.replace('__space__', ' ')
#   val = val.replace(',', ' ')

    # -- shlex.split() loses quotes in strings such '+"Word1 Word2"'
    # -- hence this approach is used to separate compound tokens    
    comp_tokens, val_rest, temp_str, quote, i = [], '', '', None, 0
    for c in val:
        if quote:
            temp_str += c
            if c == quote:
                comp_tokens.append( temp_str )
                quote = None
        else:
            if c in ("'",'"'):
                quote, temp_str = c, c
                val_rest += '__comp_token'+str(i)+'__'
                i += 1
            else:
                val_rest += c

    # -- a few translations
    val_rest = re.sub( r'(&&?|AND)',  '+', val_rest )
    val_rest = re.sub( r'(\|\|?|OR)', '|', val_rest )
    val_rest = re.sub( r'(!|NOT)',    '-', val_rest )

    val_rest = re.sub( r'([\+\-])\s+', r'\1', val_rest ) # -- remove space after + and -, but not |
    val_rest = re.sub( r'\s+', ' ', val_rest ) # -- remove multiple spaces
    val_rest = re.sub( r'([^\+\-\|\s])\s+([^\+\-\|\s])', r'\1 +\2', val_rest ) # -- put + in front of tokens not near other operators

    if mode == 'glimpse':
        val_rest = re.sub( r'\s+\|\s+', ',',  val_rest ) # -- | => ,  (OR)
        val_rest = re.sub( r'\s+\+',    ';',  val_rest ) # -- + => ;  (AND)
        val_rest = re.sub( r'\s+\-',    ';~', val_rest ) # -- - => ;~ (AND NOT)
        val_rest = val_rest.replace('(','{')
        val_rest = val_rest.replace(')','}')
        val_rest = re.sub( r'^\+', '', val_rest ) # -- remove + at head if exists
    else:
        val_rest = re.sub( r'\s+\|\s+', ' ', val_rest ) # -- take | as OR
        val_rest = re.sub( r'^([^\+\-]\w+\s+\+)', r'+\1', val_rest ) # -- put a + at head if there one after that (AND assumed)

    val_parsed = val_rest
    for i in range( len(comp_tokens) ): # -- put compound tokens back in
        val_parsed = val_parsed.replace( '__comp_token'+str(i)+'__', comp_tokens[i] )

    return val_parsed


def _make_pattern_constraint( params, value ):
    """
    This makes the constraint for ['summary'] or ['summary','description','problem']
    ~    => do a pattern search with 'like' with '%' added on either side
    !~   => do a negated pattern search with 'not like' with '%' added on either side
    else => do an index search with match() against()
    """
    if re.match( '~', value ):
       pattern = '%' + _adjust_pattern( value[1:] ) + '%'
       pattern = pattern.replace( '\\', '\\\\' ); pattern = pattern.replace( "'", "\\'" )
       constr  = '(' + ' or '. join( [p + " like '" + pattern + "'" for p in params] ) + ')'
    elif re.match( '!~', value ):
       pattern = '%' + _adjust_pattern( value[2:] ) + '%'
       pattern = pattern.replace( '\\', '\\\\' ); pattern = pattern.replace( "'", "\\'" )
       constr  = '(' + ' and '. join( [p + " not like '" + pattern + "'" for p in params] ) + ')'
    else:
       pattern = _translate_to_boolean( value )
       pattern = pattern.replace( '\\', '\\\\' ); pattern = pattern.replace( "'", "\\'" )
       constr  = "match(" + ",".join( params ) + ") against('"+pattern+"' in boolean mode )"

    return constr


def _get_constr_single( dbc, param_dic_mapped, param_names_sorted, lower=None, upper=None ):
    """
    Constructs the constrainst relevant to current_status in such a way single value tables
    do not need to be joined. e.g. current_status.status in ('Open') and resolution_id not in (14).
    If bugs that scheduled to reopen are also searched, add that part to the constraint too.
    """
    if not (param_names_sorted.has_key('in_column') or param_names_sorted.has_key('in_ref_general') or param_names_sorted.has_key('in_ref_version')): 
        return ''

    try: reopen = param_dic_mapped['reopen']
    except KeyError: reopen = ''

    constr_elems, reopen_in_query = [], False
    # -- in table params
    if param_names_sorted.has_key('in_column'):
        for param in param_names_sorted['in_column']:
            constr = eval('_'+param+"('" + str(param_dic_mapped[param]) + "')")

            if param == 'status' and reopen == 'union':
                constr_reopen = _get_reopen_constr( )
                constr = '((' + constr + ') or (' + constr_reopen + '))'

            constr_elems.append( constr )

    # -- in ref table params
    if param_names_sorted.has_key('in_ref_general'):
        for param in param_names_sorted['in_ref_general']:
            constr_elems.append( eval('_'+param+"('" + str(param_dic_mapped[param]) + "', dbc)") )

    # -- in ref table versions
    if param_names_sorted.has_key('in_ref_version'):
        for param in param_names_sorted['in_ref_version']:
            constr_elems.append( eval('_'+param+"('" + str(param_dic_mapped[param]) + "', dbc)") )

    # -- both 'description' and 'problem' do the same search: in all 'summary', 'description', and 'problem'
    if param_dic_mapped.has_key('description'):
        constr_desc = _make_pattern_constraint( ['summary','description','problem'], param_dic_mapped['description'] )
        if constr_desc: constr_elems.append( constr_desc )
    elif param_dic_mapped.has_key('problem'):
        constr_desc = _make_pattern_constraint( ['summary','description','problem'], param_dic_mapped['problem'] )
        if constr_desc: constr_elems.append( constr_desc )
    elif param_dic_mapped.has_key('summary'):
        constr_summ = _make_pattern_constraint( ['summary'], param_dic_mapped['summary'] )
        if constr_summ: constr_elems.append( constr_summ )

    # -- lower and upper bounds by bug number
    if lower:  constr_elems.append( 'current_status.bug_id >= ' + str(lower) )
    if upper:  constr_elems.append( 'current_status.bug_id <= ' + str(upper) )

    return ' and '.join( constr_elems )


def _get_multi_to_join_first( param_dic_mapped, param_names_sorted ):
    """
    Pick the first non-negated multi value table to join with current_stats.
    The goal is to join potentially the most specific (diverse values) multi-value 
    parameter table with current_status and narrow down fast in the first step.
    """
    multi_first_try = ['see_also', 'branch', 'functional_area']

    try: multi_first_try.append( param_names_sorted['multi_person'][0] )
    except: pass

    multi_first_try.extend( ['platform_affected', 'functional_category', 'component'] )

    pat, multi_first = re.compile( r'\s*!' ), None
    for param in multi_first_try:
        if param_dic_mapped.has_key(param) and not pat.search( param_dic_mapped[param] ):
            multi_first = param
            break

    return multi_first


def Find( param_dic, db='bugstats', count=1000, skip=0, lower=None, upper=None, sortby='bugnumber' ):
    """
    Find bugs by the parameters values given in param_dic. e.g. { 'Status':'Open', 'Priority':1, 'VersionReported':'9.0.0', QAContact:'shirald,carlosy' }
    will return version 9.0.0 priority 1 open bugs for which QAContacts is either shirald or carlosy.

    Single values parameters: (e.g. Status, Priority, etc.)
       * 'priority':'1,2'  => priority 1 and priority 2
       * 'priority':'!1,2' => neither priority 1 nor priority 2

    'ReportType':'Bug' is converted to 'ReportType':'!Feature,Suggestion'

    Multi value parameter: (e.q. QAContact, FunctionalArea, etc.)
       In addition to grouping and negating the group as in single value parameters, set type operators are also possible
       * 'QAContact': 'shirald & carlosy' => both  (+ and __and__ are also accepted)
       * 'QAContact': 'shirald | carlosy' => one or the other  (comma and __or__ are also accepted)
       * 'QAContact': 'shirald - carlosy' => former but not the latter (! and __not__ are also accepted.
                                             Spaces must be around '-' to differentiate them from mid word hyphens)

    summary: search in summary
    description: search in the entire description: summary, description, and problem fields
    problem: just map on to description search
        These three by default do an index search with mysql match() against() (+-~<>()*" maybe used)
        If the first character is '~', it will do a pattern search with 'like' (wild cards: '*' and '.')
        If the first two characters are '!~', it will negate the pattern search with 'not like'

    body: do a glimpse keyword search in full text body and take the intersection with the rest.
          by default the glimse search case insensitive, match whole words, and limited to first
          1000 hits. One can change this with flags given within brackets at the bigining of the
          phrase e.g. "body:[3000,cs,pw] keywords list" does case sensitive partial word match
          with an initial maximum hit count of 3000

    'reopen':0 - ignore the SeeAlso setting REOPEN_<date>
             1 - take union with the 'Status' if status include 'Open' (e.g. 'Open', '!Closed')
                 {'Status':'Open,Resolved', 'reopen':1} => open, resolved, or to be reopened.
                 take the intersection with everything else otherwise
                 {'product':'WolframAlpha', 'reopen':1} => W|A bugs to be reopened
             internally, reopen is set to '', 'union', or 'intersection'


    count is set to 1000 by default. count=0 gets all
    """
    dbc, newQ = Databases.GetDBC( db );

    def give_up():
        if newQ: dbc.close()
        return []

    param_dic_mapped = {}
    for param, val in param_dic.iteritems(): # -- map to db attr names: QAContact, qacontact,.. => qa_contact
        param_mapped = MapAttrNames( param )
        param_dic_mapped[ param_mapped ] = val 

    _normalize_reopen( param_dic_mapped )

    # -- param_names_sorted = { 'in_column':[..], 'in_ref_general':[..], 'in_ref_version':[..], 'multi_general':[..], 'multi_person':[..], 'special':[..] }:
    param_names_sorted = SortAttrNames( MapAttrNames( param_dic_mapped.keys() ) )

    # -- Plan: If constrained by params in current_status, try to join one of the multi value param assign tables
    # --       Then continue to constrain by the list of bug numbers thus obtained

    bugs = None
    if 'body' in param_dic: # -- do glimse search on full text body
        query_body   = param_dic['body']
        bugs = _get_bugs_from_glimpse( query_body )
        if not bugs: return give_up()

    constr_single     = _get_constr_single( dbc, param_dic_mapped, param_names_sorted )  # -- constr for current_status and reopen 
    param_multi_first = _get_multi_to_join_first( param_dic_mapped, param_names_sorted ) # -- prefered non-negated multi value param to join with current_status
 
    param_skip = None
    if constr_single: # -- try to join with one of the multi value assign tables
        if param_dic_mapped['reopen'] == 'union': # -- status in (<status>) or <to_be_reopened>; join with see_also
            bugs = _get_bugs_from_current_status_tab( dbc, constr_single, True, lower, upper, bugs )
            param_skip = 'reopen'
        elif param_multi_first: # -- current_status joined with one multi value parameter
            value = param_dic_mapped[ param_multi_first ]
            bugs = _find_bugs_by_multi_value_param( dbc, param_multi_first, value, lower, upper, constr_single, bugs )
            param_skip = param_multi_first
        elif param_dic_mapped['reopen'] == 'intersection': # -- <the_rest> and <to_be_reopend>; join with see_also
            bugs = _get_bugs_to_be_reopened( dbc, lower, upper, constr_single, bugs )
            param_skip = 'reopen'
        else: # -- just current_status
            bugs = _get_bugs_from_current_status_tab( dbc, constr_single, False, lower, upper, bugs )

    if isinstance(bugs,(list,tuple)) and not bugs: return give_up()

    multi_value_params = []
    for key in ['multi_person','multi_general']: # -- get the list of multi value params
        if param_names_sorted.has_key( key ): 
            multi_value_params.extend( param_names_sorted[ key ] )

    for multi_param in multi_value_params: # -- loop through multi value params
        if multi_param == param_skip: continue
        value = param_dic_mapped[ multi_param ]
        bugs  = _find_bugs_by_multi_value_param( dbc, multi_param, value, lower, upper, None, bugs )
        if not bugs: return give_up()

    if param_dic_mapped['reopen'] == 'intersection' and param_skip != 'reopen': # -- reopen == 2
        bugs = _get_bugs_to_be_reopened( dbc, lower, upper, None, bugs )

    if not bugs: return give_up()

    bugs_sorted = Sort( bugs, sortby, dbc )

    if count:
       bugs = bugs_sorted[skip:skip+count]
    else:
       bugs = bugs_sorted[skip:]

    if newQ: dbc.close()

    return bugs


def _make_update_command( bugnumber, param_dic ):
    """
    makes the update command to run. It also picks returns one (param, value) pair to check the success with
    """
    param_set, check_param, check_value = '', '', ''
    for param in param_dic.keys():
        if re.search( r'(bugnumber|addcomment|comment)', param ) : continue 
    
        value = param_dic[param]

        if isinstance( value, list ) or isinstance( value, tuple ): 
            value = ','.join( value )

        if isinstance( value, basestring ):
            value = value.strip(r', ')
            value = re.sub( r',+', ',', value.replace(' ','') )
            value = General.unique( value.split(',') )
            value = ','.join( value )

        if not check_param: # -- parameter and value to use in the check
            check_param = param
            check_value = value

        param_set = param_set + ' ' + param + "='" + str(value) + "'"

    user     = os.getlogin()

    try            : comment = param_dic['comment']
    except KeyError: comment = 'BATCH PROCESSED'

    base_set = "bugnumber="+str(bugnumber) + " user=" + user + " mode=modify ignoreunset=1 addcomment='" + comment + "' end=print:" + check_param

    command = '/bugs/modify ' + base_set + ' ' + param_set

    return command, check_param, check_value


def Update( bugnumber, param_dic, demo=False ):
    """
    Updates a bug using /bugs/modify according to the values given in param_dic.
    This function expectes parameters to be given in the right form (QAContact, but not qa_contact)
    """
    command, check_param, check_value = _make_update_command( bugnumber, param_dic )

    if demo:
        print command
    else:
        proc = subprocess.Popen( command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        proc_output, proc_error = proc.communicate()
        new_value = proc_output.rstrip("\n\r").split("\n")[-1]
        new_value = new_value.replace(' ','')

        if new_value != check_value:
            raise "BugUpdateError", "Updating bug '" + str(bugnumber) + "' failed. Checked with '" + check_param + "'. This check fails if the parameter is invalid."

    return 1


def FindBugFile( bugnumber ):
    """
    Finds the bugs data file when the bug number is given
    """
    if not bugnumber: return

    bugnum_str = "%04d" % int( bugnumber )

    bugs_root = '/math/Admin/Bugs'; # -- bugs subdirs are given relative to this
    bugs_dirs = ('OpenReports/Open.Bug','ResolvedReports/Resolved.Bug','ClosedReports/Closed.Bug','OpenReports/Open.Suggest','ResolvedReports/Resolved.Suggest','ClosedReports/Closed.Suggest','Hold')

    for sub_dir in bugs_dirs:
        bug_file = bugs_root + '/' + sub_dir + '/' + bugnum_str
        if os.path.exists( bug_file ):
            return bug_file

    return


def _get_single_value_attr( dbc, attr_get, bugnums ):
    """
    Get single value information in current_status table and single value reference tables
    """
    table = 'current_status'

    columns = []
    if 'in_column' in attr_get and attr_get['in_column']: # -- single values in column
        for attr in attr_get['in_column']: # -- in column values
            columns.append( 'current_status.'+attr);

    if 'in_index' in attr_get and attr_get['in_index']: # -- indexed single values
        for attr in attr_get['in_index']: # -- indexed in column values (no difference for this particular case)
            columns.append( 'current_status.'+attr);

    if 'in_ref_general' in attr_get and attr_get['in_ref_general']: # -- single values in reference tables
        for attr in attr_get['in_ref_general']:
             columns.append( attr + '.name as ' + attr )
             table = '(' + table + ') left join ' + attr + ' on current_status.' + attr + '_id=' + attr + '.id'

    if 'in_ref_version' in attr_get and attr_get['in_ref_version']: # -- single version values in version table
        for attr in attr_get['in_ref_version']:
             columns.append( attr + '.name as ' + attr )
             table = '(' + table + ') left join version as ' + attr + ' on current_status.' + attr + '_id=' + attr + '.id'

    bug_info     = {}
    if columns:
        columns.append( 'current_status.bug_id as bugnumber' )
    else: # -- if nothing requested, just return a hash of empty hashes (needed for next steps)
        for bug in bugnums: bug_info[bug] = {}
        return bug_info

    cursor       = dbc.cursor()
    query_common = 'select ' + ', '.join( columns ) + ' from ' + table

#    Partitioning is probably not neccessary. to restore indent following lines or delete commented out
#    for bugs_part in General.partition( bugnums, 50 ):
#        query = query_common + ' where bug_id in (' + ', '.join( map(str,bugs_part) ) + ')'

    query = query_common + ' where bug_id in (' + ', '.join( map(str,bugnums) ) + ')'
    cursor.execute( query )

    while True:
        row = cursor.fetchone()
        if not row: break
        bug_info[row['bugnumber']] = row

    return bug_info


def _attach_multi_value_attr( dbc, buginfo, attr, ref_tab, bugnums ):
    """
    Given the buginfo dictionary that is already keyed by bugnumber (along with
    single value attribute values) this attaches an array of values for the 
    specified multi value attribute
    """
    assign_tab = attr + '_assign'

    columns = assign_tab + '.bugnumber, convert(' + ref_tab + '.name, char) as name'
    table   = assign_tab + ' left join ' + ref_tab + ' on ' + assign_tab + '.' + ref_tab + '_id=' + ref_tab + '.id'
  
    if attr == 'functional_area': 
        order_by = assign_tab + '.sort_index'
    else:
        order_by = ref_tab + '.name'

    cursor = dbc.cursor()

#   Partitioning is probably not neccessary. to restore indent following lines or delete commented out
#   for bugs_part in General.partition( bugnums, 50 ):
#       constr = assign_tab + '.bugnumber in (' + ', '.join( map(str,bugs_part) ) + ') and status="current"'

    constr = assign_tab + '.bugnumber in (' + ', '.join( map(str,bugnums) ) + ') and status="current"'
    query  = 'select ' + columns + ' from ' + table + ' where ' + constr + ' order by ' + order_by
    cursor.execute( query )

    rows = cursor.fetchall()

    for row in rows:
        bugn, attr_val = row['bugnumber'], row['name']
        if bugn not in buginfo      : buginfo[bugn]       = {}
        if attr not in buginfo[bugn]: buginfo[bugn][attr] = []
        buginfo[bugn][attr].append( attr_val )

    for bugn, record in buginfo.iteritems():
        if attr not in record: record[ attr ] = []


def GetInfo( bugnums, attributes='', db='bugstats', output='dict' ):
    """
    Get information (attributes) of bugs. By default it returns a dictionary of info dictionaries
    keyed with the bugnumber. If output='list', this returns a list of dictionaries.
    """
    if not bugnums: return {}

    if isinstance( bugnums, int ):       bugnums = [ bugnums ]
    if isinstance( bugnums, basestring): bugnums = bugnums.replace(' ','').split(',')
    if isinstance( bugnums, (list,tuple) ):
       temp = map( str, bugnums );
       bugnums = map( int, filter(str.isdigit, temp) )

    if not bugnums: return {}

    if not attributes: attributes = 'summary, status, resolution, priority'

    attr_str = attributes.replace('_','').lower()
    attr_str = re.sub( r'(bugid|bugnumber)', '', attr_str ) # -- get rid of bug id/number (will add later anyway)

    attr_list = MapAttrNames( attr_str, 'list' )
    attr_get  = SortAttrNames( attr_list )

    dbc, newQ = Databases.GetDBC( db )

    buginfo = _get_single_value_attr( dbc, attr_get, bugnums )

    if 'multi_general' in attr_get and attr_get['multi_general']: # -- multi valued general attributes
        for attr in attr_get['multi_general']:
            _attach_multi_value_attr( dbc, buginfo, attr, attr, bugnums )

    if 'multi_person' in attr_get and attr_get['multi_person']: # -- multi valued personal attributes
        for attr in attr_get['multi_person']:
            _attach_multi_value_attr( dbc, buginfo, attr, 'person', bugnums )

    if newQ: dbc.close()

    if output == 'list':
        buginfo_list = []
        for bug in bugnums:
            if bug in buginfo: buginfo_list.append( buginfo[bug] )
        return buginfo_list
    else:
        return buginfo


def GetRole( user, db='bugstats' ):
    """
    get the most likely role: PrimaryDeveloper, QAContact, or ProjectManager, of the user
    """
    if user is None or user == "": return ""

    dbc, newQ = Databases.GetDBC( db )

    threshold = 1000
    query = """select    attribute from attribute_value_index 
               where     value='"""+user+"""' and attribute in ('PrimaryDeveloper','ProjectManager','QAContact') and 
                         skip=0 and score > """+str(threshold)+"""
               order by  score desc limit 1"""

    cur = dbc.cursor()
    cur.execute( query )
    row = cur.fetchone()

    if newQ: dbc.close()

    if row is None: return ""
    user_role = row['attribute']

    return user_role


if __name__ == "__main__":
    try:
#       bugs = Find( {'priority':3, 'product':'WolframAlpha', 'status':'Resolved', 'reopen':1, 'ProjectManager':'eilas' }, count=10, skip=2 )
        bugs = Find( {'Priority':3, 'Program':'WolframAlpha', 'Status':'Resolved', 'reopen':1, 'ProjectManager':'eilas' }, count=10, skip=2 )
        print bugs
    except KeyboardInterrupt:
        print "Interrupted...."
        sys.exit(0)