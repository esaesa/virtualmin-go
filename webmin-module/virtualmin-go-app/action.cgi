#!/usr/bin/perl
# virtualmin-go-app action.cgi — confirmed mutating actions (restart/rollback/prune)
use strict;
use warnings;
our (%in, %text);
do 'virtualmin-go-app-lib.pl';
&ReadParse();

my $domain = &vgo_request_domain();
&error('No valid domain was specified.') if !$domain;
my $inst = &vgo_assert_visible($domain);
my $action = $in{'action'} || '';
&error('Unknown action.') if $action !~ /^(restart|rollback|prune-releases|start|stop)$/;

if (uc($ENV{'REQUEST_METHOD'} || 'GET') ne 'POST') {
    &ui_print_header(undef, "Go $action: $domain", '', 'go');
    print "<p>Run <b>".&html_escape($action)."</b> for <b>".&html_escape($domain)."</b>?</p>\n";
    print "<form method='post' action='action.cgi'>\n";
    print "<input type='hidden' name='domain' value='".&html_escape($domain)."'>\n";
    print "<input type='hidden' name='action' value='".&html_escape($action)."'>\n";
    print "<input type='submit' value='Confirm $action'>\n";
    print "</form>\n";
    &ui_print_footer('index.cgi', 'Go Applications');
    exit;
}

&vgo_require_write($action);
my ($rc, $out) = &vgo_run($action, '--domain', $domain);
&ui_print_header(undef, "Go $action: $domain", '', 'go');
print "<pre>".&html_escape($out)."</pre>\n";
print "<p><a href='status.cgi?domain=".&vgo_url($domain)."'>Back to status</a></p>\n";
&ui_print_footer('index.cgi', 'Go Applications');
