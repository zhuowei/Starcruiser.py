#!/bin/sh
exec protoc --proto_path=/Users/zhuowei/Documents/Projects/SimStella/app/src/main/proto \
    --python_out=. --pyi_out=. \
    /Users/zhuowei/Documents/Projects/SimStella/app/src/main/proto/com/oculus/atc/atc.proto