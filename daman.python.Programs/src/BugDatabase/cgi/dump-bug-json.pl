#!/usr/bin/perl -w

use strict;
use warnings;
use CGI qw/:html2 :html3 :html4 form input textarea/;
use Data::Dumper;
use JSON -convert_blessed_universally;

use lib '/math/Admin/sqa/lib/perl';
use WRI::QA::Bugs::Bug;


my $QUERY = CGI->new;
main( $QUERY, \%ENV );

sub main {
    my ($query, $env_hr) = @_;

    my $bug;
    eval {
        my $bugnumber = $query->param('number');
        defined $bugnumber or die 'Missing bug number parameter';
        $bugnumber =~ /^ \d+ $/x or die 'Invalid bug number';

        $bug = Bug->new($bugnumber);
        $bug->fetch_data();
    } or do {
        display_error($@);
        return;
    };
    
    print CGI::header(-type=>'application/javascript', -charset=>'utf-8');
    my $prefix = CGI::param('jsonp');
    my $json = JSON->new->utf8->allow_blessed->convert_blessed;
    if (defined $prefix) {
        print $prefix, '(', $json->encode($bug), ')';
    }
    else {
        print $json->encode($bug);
    }
    return;
}

sub display_error {
    my ($message) = @_;

    print CGI::header(-type=>'text/html', -charset=>'utf-8'),
        html_head($message),
        body(
            h1('Error'),
            p($message),
        ),
        '</html>';
    return;
}

sub html_head {
    my ($title) = @_;
            
    return <<"END";
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.o$
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" >
<head>
<link rel='stylesheet' type='text/css' href='show.css' />
<title>$title</title>
</head>
END
}

