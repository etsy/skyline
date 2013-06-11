#!/bin/bash
#
# This is used to start/stop the analyzer

RETVAL=0

start () {
    rm ../src/analyzer/*.pyc
    /usr/bin/env python ../src/analyzer/analyzer-agent.py start
        RETVAL=$?
        if [[ $RETVAL -eq 0 ]]; then
            echo "started analyzer-agent"
        else
            echo "failed to start analyzer-agent"
        fi
        return $RETVAL
}

stop () {
    # TODO: write a real kill script
    ps aux | grep 'analyzer-agent.py start' | grep -v grep | awk '{print $2 }' | xargs sudo kill -9
    /usr/bin/env python ../src/analyzer/analyzer-agent.py stop
        RETVAL=$?
        if [[ $RETVAL -eq 0 ]]; then
            echo "stopped analyzer-agent"
        else
            echo "failed to stop analyzer-agent"
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
  *)
        echo $"Usage: $0 {start|stop}"
        exit 2
        ;;
esac
