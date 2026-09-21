#!/usr/bin/perl
# virtualmin-go index.cgi — dashboard of Go application instances
use strict;
use warnings;
our (%in, %text);
do 'virtualmin-go-lib.pl';
&ReadParse();

&ui_print_header(undef, 'Go Applications', '', 'go');

my @instances = &vgo_list_instances();
print "<p>".scalar(@instances)." Go application(s) configured. Ports 18100-18199.</p>\n";
if (@instances) {
    print "<table class='ui_table' width='100%'>\n";
    print "<tr><th>Domain</th><th>Version</th><th>Port</th><th>State</th><th>Actions</th></tr>\n";
    for my $inst (@instances) {
        my $dom = $inst->{'DOMAIN'};
        my $snap = &vgo_status_snapshot($dom, 10);
        my $state = $snap->{'status'};
        print "<tr>";
        print "<td><a href='status.cgi?domain=".&urlize($dom)."'>".&html_escape($dom)."</a></td>";
        print "<td>".&html_escape($inst->{'CURRENT_VERSION'} || '(none)')."</td>";
        print "<td>".&html_escape($inst->{'PORT'} || '')."</td>";
        print "<td>".&vgo_badge($state, $state)."</td>";
        print "<td><a href='status.cgi?domain=".&urlize($dom)."'>Status</a> | ".
              "<a href='validate.cgi?domain=".&urlize($dom)."'>Validate</a></td>";
        print "</tr>\n";
    }
    print "</table>\n";
}
else {
    print "<p>No Go instances yet. Enable the Go feature on a Virtualmin server, then deploy an artifact.</p>\n";
}

print "<p><a href='edit_config.cgi'>Global settings</a></p>\n";
&ui_print_footer('/', 'Webmin');
