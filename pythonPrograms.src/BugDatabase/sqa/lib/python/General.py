#!/usr/local/bin/python

import inspect, os, subprocess, re

def lockedQ( lock_file ):
    """
    If locked, returns the locked PID, else 0
    """
    if not os.path.exists( lock_file ): return 0

    fh = open( lock_file, 'r' )
    locked_pid = fh.readline().rstrip('\r\n')
    fh.close()

    try: int( locked_pid )
    except ValueError:
        raise ValueError( "Corrupt lock file" )

    proc = subprocess.Popen( "ps -p "+locked_pid+" | grep -v PID", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
    proc_output, proc_error = proc.communicate()
    output = proc_output.rstrip("\n\r")

    if output:
        return int( locked_pid )
    else:
        return 0


def lock ( lock_file ):
    """
    If already locked, returns 0, else lock and return PID
    """
    pid_curr = os.getpid()
    pid_lock = lockedQ( lock_file )
    
    if pid_lock: # -- locked
        if  pid_lock == pid_curr: return pid_curr # -- by me
        else                    : return 0        # -- by somebody else
    else: # -- not locked, lock it
        fh = open( lock_file, 'w' )
        fh.write( str( pid_curr ) + "\n" )
        fh.close()

        # -- this operation fails if a previous lock file owned by another user exists, but harmless
        try: os.chmod( lock_file, 0666 )
        except OSError: pass

        return pid_curr


def unlock( lock_file, pid_target=0 ):
    if not os.path.exists( lock_file ): return 1

    if not pid_target: pid_target = os.getpid()
    pid_locked = lockedQ( lock_file )

    if not pid_locked or pid_target == pid_locked: # -- not locked or locked by target/self
        os.remove( lock_file )
        return 1
    else:
        raise Exception( "Not locked by target process '"+str(pid_target)+"', but by process '"+str(pid_locked)+"'." ) 


def unique( var_array ):
    """
    Returns an array with only unique elements. Order preserved.
    """
    var_new, seen = [], {}
    for elem in var_array: 
        if elem in seen: 
            continue
        else: 
            var_new.append( elem )
            seen[ elem ] = 1

    return var_new


def partition( in_list, size ):

    try   : int(size)
    except: return in_list

    if size < 1: return in_list

    tmp_list = in_list[:]
    out_list = []

    while tmp_list:
        out_list.append( tmp_list[:size] )
        del tmp_list[:size]

    return out_list


def boole_to_int( val ):
    """
    convert boolean true and false to 1 and 0 as we sometimes use
    """
    if val: return 1
    else  : return 0


def csv_to_list( val ):
    """
    given a comma separated values of the form 'v1, v2, v3', this returns
    [[v1,v2,v3], False] where the second value is to indication whether or not 
    negation is intended. If '!' is inserted anywhere '!v1, v2, v3', this 
    return [[v1,v2,v3], True]. This is meant for parsing single value parameter 
    value specifications 
    """
    if val is None: return [], False

    vals_arr, negateQ = [], False

    negateQ = '!' in val

    val = val.strip(' ,') # -- spaces and commas at the ends
    val = val.replace( '!', '' )
    val = re.sub( '\s*,\s*', ',', val )

    vals_arr = list( set( val.split(',') ) )

    return vals_arr, negateQ


def set_function_opts( opts_in, opts_def ):
    """ meshes input option dict and defulat opt values dict """

    opts_out = {}

    for opt in opts_in.keys():
        opts_out[opt] = opts_in[opt]

    for opt in opts_def.keys():
        if not opts_in.has_key(opt): opts_out[opt] = opts_def[opt]

    return opts_out


def escape_xml( str ):
      
    str = str.replace( '&', '&amp;', );
    str = str.replace( '<', '&lt;',  );
    str = str.replace( '>', '&gt;',  );
    str = str.replace( "'", '&apos;' );
    str = str.replace( '"', '&quot;' );

    return str


def chomp( str ):
    if   str.endswith('\r\n') : return str[:-2]
    elif str.endswith('\n')   : return str[:-1]
    elif str.endswith('\r')   : return str[:-1]
    else                      : return str


def lineno():
    """
    Returns the line current number
    """
    return inspect.currentframe().f_back.f_lineno
