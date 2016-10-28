import codecs
import fileinput
import hashlib
import io
import os
import re
import subprocess
import sys
import time
from argparse import ArgumentParser
from datetime import datetime
from string import whitespace
from time import sleep
from traceback import format_exc

parser = ArgumentParser()
parser.add_argument('-c', '--cmdline', help='The command to run', required=True)
args = parser.parse_args()

# run a custom executable
if args.cmdline:
	exe_cmdline=args.cmdline
else:
	print "[!] You have to specify an application to execute"
	parser.print_usage()
	sys.exit(1)

# defines how long we want to run this exe
runtime = 20

# a list of path's (startswith) that are considered OK
path_whitelist = [
					r"C:\Program Files",
					os.path.expandvars(r"%USERPROFILE%"),
					r"C:\Windows"
				]

# where is procmon
procmonexe = r"ProcMon\procmon.exe"

# globals
use_pmc = False;
pmc_file = r""
pml_file = os.path.expandvars(r"%TEMP%\procmon.py.pml")
csv_file = os.path.expandvars(r"%TEMP%\procmon.py.csv")

time_exec = 0
time_process = 0
time_analyze = 0

# from noriben (https://github.com/Rurik/Noriben/blob/master/Noriben.py)
def launch_procmon_capture(procmonexe, pml_file, pmc_file):
    """
    Launch Procmon to begin capturing data
    Arguments:
        procmonexe: path to Procmon executable
        pml_file: path to Procmon PML output file
        pmc_file: path to PMC filter file
    Results:
        None
    """
    global time_exec
    time_exec = time.time()

    cmdline = '"%s" /AcceptEula /NoFilter /BackingFile "%s" /Quiet /Minimized' % (procmonexe, pml_file)
    if use_pmc:
        cmdline += ' /LoadConfig "%s"' % pmc_file
    print('[*] Running cmdline: %s' % cmdline)
    subprocess.Popen(cmdline)
    sleep(3)

# from noriben (https://github.com/Rurik/Noriben/blob/master/Noriben.py)
def terminate_procmon(procmonexe):
    """
    Terminate Procmon cleanly
    Arguments:
        procmonexe: path to Procmon executable
    Results:
        None
    """
    global time_exec
    time_exec = time.time() - time_exec

    cmdline = '"%s" /Terminate' % procmonexe
    print('[*] Running cmdline: %s' % cmdline)
    stdnull = subprocess.Popen(cmdline)
    stdnull.wait()

# from noriben (https://github.com/Rurik/Noriben/blob/master/Noriben.py)	
def process_PML_to_CSV(procmonexe, pml_file, pmc_file, csv_file):
    """
    Uses Procmon to convert the PML to a CSV file
    Arguments:
        procmonexe: path to Procmon executable
        pml_file: path to Procmon PML output file
        pmc_file: path to PMC filter file
        csv_file: path to output CSV file
    Results:
        None
    """
    global time_process
    time_convert_start = time.time()

    print('[*] Converting session to CSV: %s' % csv_file)
    cmdline = '"%s" /OpenLog "%s" /saveas "%s"' % (procmonexe, pml_file, csv_file)
    if use_pmc:
        cmdline += ' /LoadConfig "%s"' % pmc_file
    print('[*] Running cmdline: %s' % cmdline)
    stdnull = subprocess.Popen(cmdline)
    stdnull.wait()
    
    time_convert_end = time.time()
    time_process = time_convert_end - time_convert_start

# the function doing the real work	
def parse_result(csv_file,exe_to_monitor):	
	global path_whitelist
	global port_whitelist

	for line_num, original_line in enumerate(io.open(csv_file, encoding='utf-8')):
		if original_line[0] != '"':  # Ignore lines that begin with Tab.
			continue
		line = original_line.strip(whitespace + '"')
		field = line.strip().split('","')

		if field[1].lower() != exe_to_monitor.lower():
			continue
		
		""" 
			Here's the real action... Extend me...
		"""
		
		# Check if the path we access are OK
		try:
			if field[3] == 'CreateFile':
				path = field[4]
				#print "Path %s" % path
				if not path.startswith(tuple(path_whitelist)):
					if not os.path.isdir(path):
						print "[-] Access to path %s looks strange" % path
						raw_input("Press Enter to continue...")
		except:
			print "[-] Failed to parse event"
			raw_input("Press Enter to continue...")

		# Report any UDP connection
		if field[3] == 'UDP Send':	
			path = field[4]
			print "[-] We don't use UDP... %s " % path
			raw_input("Press Enter to continue...")
			
		""" 
			TODO:
				- check that we only communicate using HTTPS
				- check that we only talk to dropbox servers
				...
		"""
	
def main():
	print('[*] Starting analysis...')
	
	global procmonexe
	global use_pmc
	global pmc_file
	global pml_file
	global csv_file
	print('[*] Starting Procmon capture')
	launch_procmon_capture(procmonexe, pml_file, pmc_file)
	
	global exe_cmdline
	print('[*] Launching command line: %s' % exe_cmdline)
	subprocess.Popen(exe_cmdline,cwd=os.path.dirname(exe_cmdline))
	
	global runtime
	for i in range(runtime):
                progress = (100 / runtime) * i
                sys.stdout.write('\r%d%% complete' % progress)
                sys.stdout.flush()
                sleep(1)
	print("")
	
	print('[*] Stopping Procmon capture')
	terminate_procmon(procmonexe)
	
	child = os.path.basename(exe_cmdline)
	print('[*] Stopping child %s' % child)
	subprocess.Popen("taskkill /f /im %s" % child)
	
	print('[*] Converting to CSV')
	process_PML_to_CSV(procmonexe, pml_file, pmc_file, csv_file)
	
	print ('[*] Parsing')
	parse_result(csv_file,child)

if __name__ == '__main__':
    main()