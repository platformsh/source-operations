import logging
import sys
from logging import critical, error, info, warning, debug

CWORKING = '\033[34;1m'
# The 'color' we use to reset the colors
# @todo for some reason this is NOT resetting the colors after use
CRESET = '\033[0m\033[K'
# CRESET=$(tput sgr0 -T "${TERM}")
# bold, duh
CBOLD = '\033[1;96m'
# color we use for informational messages
CINFO = '\033[1;33m'
# color we use for warnings
CWARN = '\033[1;31m'
logging.basicConfig(format='%(message)s', level=logging.DEBUG, stream=sys.stdout)
logging.addLevelName(logging.WARNING, "%s%s%s" % (CWARN, logging.getLevelName(logging.WARNING), CRESET))
logging.addLevelName(logging.ERROR, "%s%s%s" % (CWARN, logging.getLevelName(logging.ERROR), CRESET))


def outputError(cmd, output):
    logging.warning("{}{}{}{} command failed!{}".format(CBOLD, cmd, CRESET, CWARN, CRESET))
    logging.info("See the following output:")
    logging.info(output)
    # @todo exit seems... dirty?
    # sys.exit("See previous error above")
    return False
