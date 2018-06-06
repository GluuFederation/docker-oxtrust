#!/bin/sh

if [ -z $GLUU_SHIB_SOURCE_DIR ]; then
    echo "[shibwatcher/ERROR] source directory must be set"
    exit 1
else
    mkdir -p $GLUU_SHIB_SOURCE_DIR
fi

if [ -z $GLUU_SHIB_TARGET_DIR ]; then
    echo "[shibwatcher/ERROR] target directory must be set"
    exit 1
else
    mkdir -p $GLUU_SHIB_TARGET_DIR
fi

echo "[shibwatcher/INFO] Running shibwatcher <source=$GLUU_SHIB_SOURCE_DIR,target=$GLUU_SHIB_TARGET_DIR>"

inotifywait -mrq -e close_write,moved_to $GLUU_SHIB_SOURCE_DIR | while read path event file
do
    ext=${file##*.}
    case $ext in
        xml|config|xsd|dtd)
            src=$path$file
            dest=$(echo "$src" | sed "s@$GLUU_SHIB_SOURCE_DIR@$GLUU_SHIB_TARGET_DIR@")
            dest_dir=$(dirname $dest)

            echo "[shibwatcher/INFO] Got event ${event} on ${src}"
            echo "[shibwatcher/INFO] Copying ${src} to ${dest}"
            if [ ! -d $dest_dir ]; then
                mkdir -p $dest_dir
            fi
            cp $src $dest
        ;;
    esac
done
