import csv, re
import sys, os

from xml.etree import ElementTree as ET

RE_resultLog = re.compile("^(.*) \[(.*)\]$")
RE_clangVerison = re.compile("^clang version (.*) \((.*)\.git (.*)\)")
RE_gitCommitHash = re.compile("^[0-9abcdef]+$")

def colorizeMake(td, val):
	if val == 'e_cmp':
		td.set('bgcolor', '#f70000')
	elif val == 'e_lnk':
		td.set('bgcolor', '#f77300')
	elif val == 'ICE':
		td.set('bgcolor', '#c2024f')
	elif val == 'built':
			return 0
	return 1

def colorizeCTest(td, val):
	if val == '***Failed':
			td.set('bgcolor', '#f70000')
	elif val == 'Subprocess aborted***Exception:':
			td.set('bgcolor', '#ce0000')
	elif val == '***Timeout':
			td.set('bgcolor', '#f77300')
	elif val == '***Not Run':
			td.set('bgcolor', '#f7f700')
	elif val == 'Passed':
			td.set('bgcolor', '#00f700')
			return 0
	elif val == 'None':
			return 0
	return 1

def shrinkLongText(td, val):
	td.set('title', val)
	td.set('style', "font-size:4pt;")
	return 0

colorize = [
		lambda td, val : 0,
		colorizeMake,
		colorizeCTest,
		lambda td, val : 0,
		shrinkLongText,
	]

def colorizeIdx(c):
	return c if c < len(colorize) else 0

fname = sys.argv[1]
with open(fname, 'r') as f:
	reader = csv.reader(f, delimiter='\t')

	html = ET.Element('html')
	doc = ET.ElementTree(html)

	head = ET.SubElement(html, 'head')
	css = ET.SubElement(head, 'style')
	css.text = """
	table, th, td {
		border: 1px solid black;
		border-collapse: collapse;
	}
	"""

	sortableScript = None
	try:
		with open(os.path.join(re.sub("[^/]+$", '', sys.argv[0]), "blob/sortable.js"), 'r') as f:
			sortableScript = ET.SubElement(head, 'script')
			sortableScript.text = f.read()
	except FileNotFoundError as e:
		print(e.strerror, e.filename)

	colTypeMap = None
	ntests = 0

	body = ET.SubElement(html, 'body')
	tab = ET.SubElement(body, 'table')
	tab.set('id', 'table')
	for i, row in enumerate(reader):
		tr = ET.SubElement(tab, 'tr')
		if i == 0:
			colTypeMap = [0]*len(row)
			prev = None
			rep = 0
			tests = {}
			for a in sorted(row):
				if prev is None:
					prev = a
				elif a == prev:
					rep += 1
				else:
					if rep > 0: 
						tests[prev] = 0
					prev = a
					rep = 0
			if rep > 0: 
				tests[prev] = 0
			ntests = len(tests)

			colHeadColors = [None, '#55aaff', '#00aa7f', '#ffaa00']
			for c, cell in enumerate(row):
				td = ET.SubElement(tr, 'th')
				td.text = cell
				if sortableScript is not None:
					td.set('onclick', 'sortTable({})'.format(c))

				if cell in tests:
					tests[cell] += 1
					colTypeMap[c] = tests[cell]
					td.set('bgcolor', colHeadColors[colTypeMap[c]])
				elif cell == 'CXX' or cell == 'CXX_FLAGS':
					colTypeMap[c] = 4

			td = ET.SubElement(tr, 'td')
			td.text = "build failures"
			td = ET.SubElement(tr, 'td')
			td.text = "run failures"

		else:
			badCount = [0]*len(colorize)
			for c, cell in enumerate(row):
				td = ET.SubElement(tr, 'td')
				m = RE_resultLog.match(cell)
				if m:
					a = ET.SubElement(td, 'a')
					val = m.groups()[0]
					a.text =  val
					a.set('href', m.groups()[1])
					# a.set('type', 'text/plain')
					a.set('target', 'new')
				else:
					m = RE_clangVerison.match(cell)
					if m:
						a = ET.SubElement(td, 'a')
						val = "clang {}".format(m.groups()[0])
						a.text = val
						a.set('href', "{}/commit/{}".format(m.groups()[1], m.groups()[2]))
					else:
						m = RE_gitCommitHash.match(cell)
						if m:
							a = ET.SubElement(td, 'a')
							val = cell
							a.text = val
							a.set('href', "https://github.com/alpaka-group/alpaka/commit/{}".format(cell))
						else:
							val = cell
							td.text = val
				ct = colTypeMap[c]
				badCount[ct] += colorize[ct](td, val)

			td = ET.SubElement(tr, 'td')
			td.text = "{}/{}".format(badCount[1], ntests)
			td = ET.SubElement(tr, 'td')
			td.text = "{}/{}".format(badCount[2], ntests)

	doc.write(re.sub("[^.]+$", 'html', fname), method='html')
