#!/bin/bash
ARGS=4
if [ $# -ne "$ARGS" ]
then
    echo "Usage: `basename $0` channel_hash download_dir crawle_port"
exit 0
fi


url="https://www.youtube.com/playlist?list="$1
channel_url="https://www.youtube.com/channel/$1/playlists"
proxy="--proxy socks5://localhost:1080"
args="--no-check-certificate --restrict-filenames --no-warnings --ignore-errors"
get_info=" --get-id --get-filename --get-title"
get_sub="--write-auto-sub --skip-download"
filename_template=" -o %(uploader)s/%(playlist)s/%(playlist_index)s--%(title)s.%(ext)s"

download_dir=$2
name=${download_dir##*/}
list_path=$download_dir"/$name.txt"

if [ ! -d $download_dir ]; then
  echo "mkdir -p $download_dir"
  mkdir -p $download_dir
fi

port=$3
echo "port is $port"
echo "crawle task to "$list_path

#爬取下载列表
echo "youtube-dl  $filename_template $get_info $proxy $channel_url"
youtube-dl  $filename_template $get_info $proxy $channel_url > $list_path

#添加下载任务
python crawle_c.py $list_path $download_dir $port

cd $download_dir
#下载字幕
echo "youtube-dl  $channel_url  $args $get_sub $proxy $filename_template"
youtube-dl  $channel_url  $args $get_sub $proxy $filename_template
