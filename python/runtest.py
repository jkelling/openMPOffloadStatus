#!/usr/bin/env python3

import re
import subprocess
import os, socket
import hashlib

RE_step = re.compile("^\[ *([0-9]*)%\] (.*) ([^\s]+)$")
RE_targetFromObject = re.compile("^.*/([^/]+)\.dir/(.*)\.o$")
RE_targetConsolidate = re.compile("^Consolidate compiler generated dependencies of target (.*)$")

RE_cmakeCacheLine = re.compile("^([^:]+):([^=]+)=(.*)$")

RE_ctestResult = re.compile("^ *([0-9]+)/([0-9]+) Test.*: ([^ ]+) \.* *([a-zA-Z*]+) *([0-9.]+) ([a-z]+)$")
RE_ctestStart = re.compile("^ *Start.*: ([^ ]+).*$")

class TargetInfo:
	def __init__(self, name, action, log = None):
		self.name = name
		self.action = action
		self.log = log
		self.testResult = None
		self.testLog = None
		self.testTime = None

targets = []
targetsMap = {}

ActionsMap = {
		"Built target" : "built",
		"Building CXX object" : "e_cmp",
		"Linking CXX executable" : "e_lnk",
	}

# IN = "CMakeCache.txt"
IN = "/home/kelling/checkout/alpaka/buildClang15_hsa/CMakeCache.txt"
cmakeCache = {}
try:
	with open(IN) as f:
		for line in f:
			match = RE_cmakeCacheLine.match(line)
			if match:
				cmakeCache[match.groups()[0]] = match.groups()[1:]
except OSError:
	raise RuntimeError("Not inside a cmake build dir.")

OUTDIR = "testOut"
os.mkdir(OUTDIR)

f = subprocess.run("make -k 2>&1", stdout=subprocess.PIPE, shell=True)
# f = subprocess.run("cat /home/kelling/checkout/alpaka/buildClang15_hsa/log 2>&1", stdout=subprocess.PIPE, shell=True)
log = []
for line in f.stdout.decode("utf-8").strip().split('\n'):
	match = RE_step.match(line)
	if match:
		action = match.groups()[1]
		target = match.groups()[2]
		if action == "Building CXX object":
			match = RE_targetFromObject.match(target)
			if not match:
				raise RuntimeError("Invalid 'building object' line: '{}'.".format(target))
			target = match.groups()[0]

		if not action in ActionsMap:
			raise RuntimeError("Unknown axction '{}'.".format(action))
		action = ActionsMap[action]

		if not targets or targets[-1].name != target:
			targets.append(TargetInfo(target, action, '\n'.join(log) if log else None))
			targetsMap[targets[-1].name] = targets[-1]
			log = []
		else:
			targets[-1].action = action
		continue

	match = RE_targetConsolidate.match(line)
	if match:
		continue

	log.append(line)

f = subprocess.run("ctest --output-on-failure --timeout 120 2>&1", stdout=subprocess.PIPE, shell=True)
# f = subprocess.run("cat /home/kelling/checkout/alpaka/buildClang15_hsa/ctest.log 2>&1", stdout=subprocess.PIPE, shell=True)
target = None
log = []
for line in f.stdout.decode("utf-8").strip().split('\n'):
	if target is None:
		match = RE_ctestResult.match(line)
		if match:
			target = match.groups()[2]
			result = match.groups()[3]
			targetsMap[target].testResult = result
			targetsMap[target].testTime = float(match.groups()[4])
			if result != "Passed":
				continue
		else:
			continue
	else:
		match = RE_ctestStart.match(line)
		if not match:
			log.append(line)
			continue

	if log:
		targetsMap[target].testLog = '\n'.join(log)
		log = []
	target = None

HOSTNAME = socket.gethostname()
CXX = cmakeCache["CMAKE_CXX_COMPILER"][1]
CXX_FLAGS = cmakeCache["CMAKE_CXX_FLAGS"][1]
TGTARCH = "??"
if re.search("amdgcn-amd-amdhsa", CXX_FLAGS):
	TGTARCH = "HSA"

f = subprocess.run("{} --version | head -n1".format(CXX), stdout=subprocess.PIPE, shell=True)
CXX_VERSION = f.stdout.decode("utf-8").strip()

m = hashlib.sha1()
m.update(HOSTNAME.encode())
m.update(CXX.encode())
m.update(CXX_FLAGS.encode())
m.update(CXX_VERSION.encode())
ID = m.digest().hex()
os.mkdir(os.path.join(OUTDIR, ID))

with open(os.path.join(OUTDIR, "out.dat"), 'w') as f:
	DELIM = '\t'
	f.writelines(DELIM.join(['']*2 + [DELIM.join(x.name for x in targets)]*3 + ['']*2) + '\n')
	actions = []
	results = []
	c = 0
	for t in targets:
		a = str(t.action)
		if t.log is not None:
			logout = "{}/{}.log".format(ID, c)
			a = "{} [{}]".format(a, logout)
			with open(os.path.join(OUTDIR, logout), 'w') as fl:
				fl.writelines(t.log)
			c += 1
		actions.append(a)

		r = str(t.testResult)
		if t.testLog is not None:
			logout = "{}/{}.log".format(ID, c)
			r = "{} [{}]".format(r, logout)
			with open(os.path.join(OUTDIR, logout), 'w') as fl:
				fl.writelines(t.testLog)
			c += 1
		results.append(r)

	f.writelines(
		DELIM.join([TGTARCH, CXX_VERSION] + actions + results +
			[str(x.testTime) for x in targets] + [CXX, CXX_FLAGS]) + '\n')
