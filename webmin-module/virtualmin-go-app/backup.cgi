#!/usr/bin/perl
# virtualmin-go-app backup.cgi — create app backups + list history.
# Restore stays CLI-only in v0.2 (destructive); this page links the command.
use strict;
use warnings;
our (%in, %text);
do 'virtualmin-go-app-lib.pl';
&ReadParse();

my @instances = &vgo_visible_instances();
&error('No Go instances are visible to your login.') if !@instances;

my ($message, $type, $details) = ('', 'info', '');
if (uc($ENV{'REQUEST_METHOD'} || 'GET') eq 'POST' && $in{'create'}) {
    &vgo_require_write('backup creation');
    my $domain = lc($in{'domain'} || '');
    my $inst = &vgo_assert_visible($domain);
    my ($dest, $err) = vgo_new_backup_path($domain);
    &error($err) if !$dest;
    my ($rc, $out) = vgo_run('backup', '--domain', $domain, '--dest', $dest);
    $message = $rc == 0 ? "Backup created: $dest" : 'Backup failed.';
    $type = $rc == 0 ? 'good' : 'bad';
    $details = $out;
}

my $domain = lc($in{'domain'} || $instances[0]->{'DOMAIN'});
my $inst = &vgo_assert_visible($domain);
my @backups = vgo_list_backups($domain);

&ui_print_header(undef, "Go Backups: $domain", '', 'go');
if ($message) {
    print "<p><b>".vgo_html($message)."</b></p>\n";
    print "<pre>".vgo_html($details || '')."</pre>\n" if $details;
}
my $opts = join('', map {
    my $d = $_->{'DOMAIN'};
    "<option value='".vgo_html($d)."'".($d eq $domain ? ' selected' : '').">".vgo_html($d)."</option>";
} @instances);
print &ui_form_start('backup.cgi', 'post');
print &ui_table_start('Create backup', 'width=100%', 2);
print &ui_table_row('Domain', "<select name='domain'>$opts</select>");
print &ui_table_end();
print &ui_form_end([['create', 'Create backup now']]);
if (@backups) {
    print "<table class='ui_table' width='100%'>\n";
    print "<tr><th>Archive</th><th>Size</th><th>Created</th></tr>\n";
    for my $b (@backups) {
        print "<tr><td>".vgo_html($b->{'name'})."</td><td>".vgo_html(vgo_nice_size($b->{'size'}))."</td>".
              "<td>".vgo_html(scalar(localtime($b->{'mtime'})))."</td></tr>\n";
    }
    print "</table>\n";
}
else {
    print "<p>No backups yet for $domain.</p>\n";
}
print "<p>Restore is CLI-only in v0.2: <tt>virtualmin-go-app restore --domain $domain --source FILE.tar.gz</tt></p>\n";
print "<p><a href='index.cgi'>All instances</a></p>\n";
&ui_print_footer('index.cgi', 'Go Applications');
