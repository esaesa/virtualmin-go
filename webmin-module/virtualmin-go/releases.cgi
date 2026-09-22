#!/usr/bin/perl
# virtualmin-go releases.cgi — per-domain release table + rollback/prune.
use strict;
use warnings;
our (%in, %text);
do 'virtualmin-go-lib.pl';
&ReadParse();

my $domain = &vgo_request_domain();
&error('No valid domain was specified.') if !$domain;
my $inst = &vgo_assert_visible($domain);

my ($message, $type, $details) = ('', 'info', '');
if (uc($ENV{'REQUEST_METHOD'} || 'GET') eq 'POST' && $in{'op'}) {
    &vgo_require_write('release operation');
    my $op = $in{'op'};
    if ($op eq 'rollback') {
        &error('Confirmation must match the domain.') if ($in{'confirm_value'} || '') ne $domain;
        my ($rc, $out) = vgo_run_opts({ timeout => 300 }, 'rollback', '--domain', $domain);
        $message = $rc == 0 ? 'Rolled back to the previous release.' : 'Rollback failed.';
        $type = $rc == 0 ? 'good' : 'bad';
        $details = $out;
    }
    elsif ($op eq 'prune') {
        my $keep = $in{'keep'} || '5';
        &error('Keep must be a number >= 2.') if $keep !~ /^\d+$/ || $keep < 2;
        my ($rc, $out) = vgo_run('prune-releases', '--domain', $domain, '--keep', $keep);
        $message = $rc == 0 ? "Pruned releases (keeping newest $keep)." : 'Prune failed.';
        $type = $rc == 0 ? 'good' : 'bad';
        $details = $out;
    }
    else {
        &error('Unknown release operation.');
    }
    $inst = vgo_load_instance($domain) || $inst;
}

&ui_print_header(undef, "Go Releases: $domain", '', 'go');
if ($message) {
    print "<p><b>".vgo_html($message)."</b></p>\n";
    print "<pre>".vgo_html($details || '')."</pre>\n" if $details;
}
my ($rc, $out) = vgo_run_opts({ timeout => 30 }, 'releases', '--domain', $domain, '--json');
my $data = vgo_json_from_output($out) || {};
my $cur = $data->{'current'} || '';
my $prev = $data->{'previous'} || '';
my @rels = ref($data->{'releases'}) eq 'ARRAY' ? @{$data->{'releases'}} : ();
if (@rels) {
    print "<table class='ui_table' width='100%'>\n";
    print "<tr><th>Release</th><th>Version</th><th>Role</th></tr>\n";
    for my $r (sort { $b->{'id'} cmp $a->{'id'} } @rels) {
        my $role = $r->{'id'} eq $cur ? 'current' : ($r->{'id'} eq $prev ? 'previous' : 'older');
        print "<tr><td>".vgo_html($r->{'id'})."</td><td>".vgo_html($r->{'version'} || '-')."</td><td>$role</td></tr>\n";
    }
    print "</table>\n";
}
else {
    print "<p>No releases deployed yet.</p>\n";
}
print &ui_form_start('releases.cgi', 'post');
print "<input type='hidden' name='domain' value='".vgo_html($domain)."'>";
print &ui_table_start('Rollback', 'width=100%', 2);
print &ui_table_row('Target', 'previous release'.($prev ? " (<tt>".vgo_html($prev)."</tt>)" : ' (none)'));
print &ui_table_row('Confirm', &ui_textbox('confirm_value', '', 30)." (retype <tt>".vgo_html($domain)."</tt>)");
print &ui_table_end();
print "<input type='hidden' name='op' value='rollback'>";
print &ui_form_end([['rollback', 'Roll back now']]);
print &ui_form_start('releases.cgi', 'post');
print "<input type='hidden' name='domain' value='".vgo_html($domain)."'>";
print &ui_table_start('Prune old releases', 'width=100%', 2);
print &ui_table_row('Keep newest', &ui_textbox('keep', '5', 6)." (current+previous always protected)");
print &ui_table_end();
print "<input type='hidden' name='op' value='prune'>";
print &ui_form_end([['prune', 'Prune now']]);
print "<p><a href='deploy.cgi?domain=".vgo_url($domain)."'>Deploy</a> | <a href='status.cgi?domain=".vgo_url($domain)."'>Status</a></p>\n";
&ui_print_footer('index.cgi', 'Go Applications');
