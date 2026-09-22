#!/usr/bin/perl
# virtualmin-go operations.cgi — bulk validate/restart across visible
# instances with typed confirmation (mirrors PB operations page).
use strict;
use warnings;
our (%in, %text);
do 'virtualmin-go-lib.pl';
&ReadParse();

my @instances = &vgo_visible_instances();
&error('No Go instances are visible to your login.') if !@instances;

my %commands = (validate => 0, restart => 1, status => 0);
my ($message, $type, $details) = ('', 'info', '');

if (uc($ENV{'REQUEST_METHOD'} || 'GET') eq 'POST' && $in{'execute'}) {
    my $action = lc($in{'action'} || '');
    &error('Unknown bulk action.') if !exists($commands{$action});
    if ($commands{$action}) {
        &vgo_require_write('bulk operation');
        &error('Bulk confirmation did not match the action name.')
            if lc($in{'confirm_action'} || '') ne $action;
    }
    my @requested = split(/\0|,/, $in{'domains'} || '');
    my %want = map { lc($_) => 1 } @requested;
    my @targets = grep { $want{lc($_->{'DOMAIN'})} } @instances;
    &error('No matching visible instances selected.') if !@targets;
    my (@ok, @fail);
    for my $inst (@targets) {
        my $dom = $inst->{'DOMAIN'};
        my ($rc, $out) = vgo_run_opts({ audit_read => ($action eq 'validate' ? 1 : 0) },
                                       $action, '--domain', $dom);
        if ($rc == 0) { push(@ok, $dom); }
        else { push(@fail, "$dom: ".substr($out || 'failed', 0, 200)); }
    }
    $message = "Bulk $action: ".scalar(@ok)." ok, ".scalar(@fail)." failed.";
    $type = @fail ? 'bad' : 'good';
    $details = join("\n", @fail);
}

&ui_print_header(undef, 'Go Operations', '', 'go');
if ($message) {
    print "<p><b>".vgo_html($message)."</b></p>\n";
    print "<pre>".vgo_html($details)."</pre>\n" if $details;
}
print "<p>Run an action across your instances. Mutating actions need the action name retyped as confirmation.</p>\n";
print &ui_form_start('operations.cgi', 'post');
print &ui_table_start('Bulk operation', 'width=100%', 2);
print &ui_table_row('Action',
    "<select name='action'><option value='validate'>validate</option><option value='status'>status</option><option value='restart'>restart</option></select>");
my $boxes = join('<br>', map {
    my $d = $_->{'DOMAIN'};
    "<label><input type='checkbox' name='domains' value='".vgo_html($d)."' checked> ".vgo_html($d)."</label>";
} @instances);
print &ui_table_row('Instances', $boxes);
print &ui_table_row('Confirm', &ui_textbox('confirm_action', '', 16)." (retype action for restart)");
print &ui_table_end();
print &ui_form_end([['execute', 'Run bulk operation']]);
print "<p><a href='index.cgi'>All instances</a></p>\n";
&ui_print_footer('index.cgi', 'Go Applications');
