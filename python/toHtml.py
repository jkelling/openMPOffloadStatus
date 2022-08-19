import csv, re
import sys

from xml.etree import ElementTree as ET

RE_reultLog = re.compile("^(.*) \[(.*)\]$")

fname = sys.argv[1]
with open(fname, 'r') as f:
	reader = csv.reader(f, delimiter='\t')

	tab = ET.Element('table')
	doc = ET.ElementTree(tab)

	for i, row in enumerate(reader):
		tr = ET.SubElement(tab, 'tr')
		for cell in row:
			td = ET.SubElement(tr, 'th' if i == 0 else 'td')

			match = RE_reultLog.match(cell)
			if match:
				a = ET.SubElement(td, 'a')
				a.text = match.groups()[0]
				a.set('href', match.groups()[1])
			else:
				td.text = cell

	doc.write(re.sub("[^.]+$", 'html', fname))
