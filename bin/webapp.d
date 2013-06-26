#!/bin/bash
#
# This is used to start/stop webapp 

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/.."
RETVAL=0

start () {
    rm -f $BASEDIR/src/webapp/*.pyc
    /usr/bin/env python $BASEDIR/src/webapp/webapp.py start
        RETVAL=$?
        if [[ $RETVAL -eq 0 ]]; then
            echo "started webapp"
        else
            echo "failed to start webapp"
        fi
        return $RETVAL
}

stop () {
    /usr/bin/env python $BASEDIR/src/webapp/webapp.py stop
        RETVAL=$?
        if [[ $RETVAL -eq 0 ]]; then
            echo "stopped webapp"
        else
            echo "failed to stop webapp"
        fi
        return $RETVAL
}

restart () {
    rm -f $BASEDIR/src/webapp/*.pyc
    /usr/bin/env python $BASEDIR/src/webapp/webapp.py restart
        RETVAL=$?
        if [[ $RETVAL -eq 0 ]]; then
            echo "restarted webapp"
        else
            echo "failed to restart webapp"
        fi
        return $RETVAL
}

# See how we were called.
case "$1" in
  start)
    start
        ;;
  stop)
    stop
        ;;
  restart)
    restart
    ;;

  *)
        echo $"Usage: $0 {start|stop}"
        exit 2
        ;;
esac
