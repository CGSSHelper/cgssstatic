# from http://stackoverflow.com/questions/4264379/it-is-possible-export-table-sqlite3-table-to-csv-or-similiar
""" Usage
conn = sqlite3.connect('yourdb.sqlite')

c = conn.cursor()
c.execute('select * from yourtable')

writer = UnicodeWriter(open("export.csv", "wb"))

writer.writerows(c)
"""
try:
    import csv, codecs, cStringIO
except ImportError: #python3
    import csv, codecs
    from io import StringIO

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f", 
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([str(s).encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)
