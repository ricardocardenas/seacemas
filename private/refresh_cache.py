import sys
from seaceperu import *
import datetime

command = sys.argv[0]
usage = "Usage: %s [-d dd/mm/YYYY] [word1] [word2...]" % command

if len(sys.argv) == 1:
    print usage
    sys.exit()
if sys.argv[1] == '-d':
    if len(sys.argv) == 3:
        try:
            d = datetime.datetime.strptime(sys.argv[2], "%d/%m/%Y")
        except ValueError:
            print "Error: Date must be in dd/mm/yyyy format."
            print usage
            sys.exit()
        convocatorias = SEACE.search_date(d)
    else:
        print "Error: no date provided after -d."
        print usage
        sys.exit()
else:
    words = ' '.join(sys.argv[1:])
    convocatorias = SEACE.search_words(words)

n = SEACE.get_convocatorias(db, convocatorias)
print "%d convocatorias added or refreshed." % n
