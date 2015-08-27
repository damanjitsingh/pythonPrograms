import sys
import Databases

class Bug:


    def __init__( self, number=None ):
        self.number = number
        self.data   = {}


    def __repr__( self ):
        return str(self.number) + ":" + str( self.data )


    def set( self, what, value ):
        if what == 'data':
            self.data = value
        elif what == 'number':
            self.number = value
        else:
            self.data[what] = value
  

    def get( self, what ):
        if what == 'data':
            return self.data
        elif what == 'number':
            return self.number
        else:
            try:
                return self.data[what]
            except KeyError:
                return None


    def _fetch_data_single( self, dbc ):
        """
        fetch single valued data from MySQL part of the database
        """
        cur = dbc.cursor()

        table   = 'current_status'
        columns =           'bug_id as bugnumber,summary,description,problem,priority,magnitude,newbie_project,volunteer_project,pure_math_project'
        columns = columns + ',date_reported,date_resolved,status,last_update'

        for attr in ('product','report_type','resolution'):
            table   = '(' + table + ') left join ' + attr + ' on current_status.' + attr + '_id=' + attr + '.id'
            columns = columns + ',' + attr + '.name as ' + attr

        for attr in ('version_reported','resolution_version'):
            table   = '(' + table + ') left join version as ' + attr + ' on current_status.' + attr + '_id=' + attr + '.id'
            columns = columns + ',' + attr + '.name as ' + attr

        query = 'select ' + columns + ' from ' + table + ' where bug_id=' + str( self.number )
        cur.execute(query)

        row = cur.fetchone()
        cur.close()

        return row


    def _fetch_data_multi( self, attr, dbc ):
        """
        fetch multi valued data for a particular attribute from MySQL part of the database 
        """
        cur = dbc.cursor()

        assign_tab = attr + '_assign'
        if attr in ('reported_by','primary_developer','project_manager','qa_contact','resolved_by','resolve_tested_by','review_completed_by'):
            ref_tab = 'person'
        else:
            ref_tab = attr

        table = assign_tab + ' left join ' + ref_tab + ' on ' + assign_tab + '.' + ref_tab + '_id=' + ref_tab + '.id'

        if attr == 'functional_area':
            sortby = assign_tab + '.sort_index'
        else:
            sortby = ref_tab + '.name'

        query = 'select ' + ref_tab + '.name from ' + table + ' where bugnumber=' + str(self.number) + ' and ' + assign_tab + '.status="current" order by ' + sortby
        cur.execute( query )

        rows = cur.fetchall()
        def ext(a): return a['name']
        values = map( ext, rows )

        cur.close()

        return values


    def fetch_data( self, db='bugstats' ):
        """
        fetch data from MySQL part of the database
        """
        if not isinstance( self.number, (int,long) ): 
            raise TypeError, "bug number is not an integer"

        dbc, newQ = Databases.GetDBC( db )

        data = self._fetch_data_single( dbc )

        attr_multi =  ('component','functional_category','functional_area','reported_by','primary_developer','project_manager','qa_contact',
                       'resolved_by','resolve_tested_by','review_completed_by','see_also','platform_affected','branch')

        for attr in attr_multi:
            values = self._fetch_data_multi( attr, dbc )
            data[attr] = values

        if newQ: dbc.close()

        self.data = data
