#!/bin/bash

if [ $# -lt 1 ]; then
	echo Usage: $(basename $0) version
	exit 1
fi

PROJECT_DIR=$(pwd)
APPCFG_BIN="$HOME/opt/google_appengine/appcfg.py"
SVN_HOST="https://konverta4.googlecode.com/svn"
SVN_TRUNK="$SVN_HOST/trunk"
SVN_TAG="$SVN_HOST/tags/$1"
API_KEY=$(cat api.key)

echo "Saved backup..."
mv api4.py api4.py.orig
echo "Replaced API key..."
sed "s/API_KEY\ =\ \"Demo\"/API_KEY\ =\ \"$API_KEY\"/g" api4.py.orig >api4.py
echo "Uploading application..."
$APPCFG_BIN --email="renatn@gmail.com" update $PROJECT_DIR
echo "Restored backup..."
mv api4.py.orig api4.py
echo "Creating svn tag..."
svn copy $SVN_TRUNK $SVN_TAG -m "Created tag for appspot version $1"
