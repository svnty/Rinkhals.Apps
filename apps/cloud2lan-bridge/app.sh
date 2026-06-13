. /useremain/rinkhals/.current/tools.sh

APP_ROOT=$(dirname $(realpath $0))

status() {
    PID=$(get_by_name cloud2lan-bridge.py)

    if [ "$PID" == "" ]; then
        report_status $APP_STATUS_STOPPED
    else
        report_status $APP_STATUS_STARTED "$PID"
    fi
}
start() {
    stop

    cd $APP_ROOT

    chmod +x cloud2lan-bridge.sh
    ./cloud2lan-bridge.sh &
}
stop() {
    # Kill the supervisor first so it doesn't immediately respawn the python.
    kill_by_name cloud2lan-bridge.sh
    kill_by_name cloud2lan-bridge.py
    
    # Clean up the streaming pipeline and helper processes
    pkill -f auto_stream.sh 2>/dev/null
    pkill -f agora_pusher 2>/dev/null
    pkill -f "ffmpeg -nostdin -loglevel quiet -i http://127.0.0.1:18088/flv" 2>/dev/null
    pkill -f "nc 127.0.0.1 18086" 2>/dev/null
}

case "$1" in
    status)
        status
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    *)
        echo "Usage: $0 {status|start|stop}" >&2
        exit 1
        ;;
esac
