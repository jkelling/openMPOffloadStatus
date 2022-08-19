import csv, re
import sys

from xml.etree import ElementTree as ET

RE_resultLog = re.compile("^(.*) \[(.*)\]$")
RE_clangVerison = re.compile("^(clang version .* )\((.*)\)")

def colorizeMake(td, val):
	match val:
		case 'e_cmp':
			td.set('bgcolor', '#f70000')
		case 'e_lnk':
			td.set('bgcolor', '#f77300')
		case 'built':
			return 1
	return 0

def colorizeCTest(td, val):
	match val:
		case '***Failed':
			td.set('bgcolor', '#f70000')
		case '***Timeout':
			td.set('bgcolor', '#f77300')
		case 'Passed':
			td.set('bgcolor', '#00f700')
			return 1
	return 0

colorize = [
		lambda td, val : 0,
		colorizeMake,
		colorizeCTest,
		lambda td, val : 0,
	]

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

	colTypeMap = None
	ntests = 0

	body = ET.SubElement(html, 'body')
	tab = ET.SubElement(body, 'table')
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

				if cell in tests:
					tests[cell] += 1
					colTypeMap[c] = tests[cell]
					td.set('bgcolor', colHeadColors[colTypeMap[c]])

			td = ET.SubElement(tr, 'td')
			td.text = "build success"
			td = ET.SubElement(tr, 'td')
			td.text = "run success"

		else:
			goodCount = [0]*len(colorize)
			for c, cell in enumerate(row):
				td = ET.SubElement(tr, 'td')
				match = RE_resultLog.match(cell)
				if match:
					a = ET.SubElement(td, 'a')
					val = match.groups()[0]
					a.text =  val
					a.set('href', match.groups()[1])
					# a.set('type', 'text/plain')
					a.set('target', 'new')
				elif match := RE_clangVerison.match(cell):
					a = ET.SubElement(td, 'a')
					val = match.groups()[0]
					a.text =  val
					a.set('href', match.groups()[1])
				else:
					val = cell
					td.text = val
				goodCount[colTypeMap[c]] += colorize[colTypeMap[c]](td, val)

			td = ET.SubElement(tr, 'td')
			td.text = "{}/{}".format(goodCount[1], ntests)
			td = ET.SubElement(tr, 'td')
			td.text = "{}/{}".format(goodCount[2], ntests)

	doc.write(re.sub("[^.]+$", 'html', fname))
