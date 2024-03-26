#!/bin/bash
rm -rf GraphXplore/graphxplore
cp -r ../graphxplore GraphXplore/graphxplore
npm install
npm run dump GraphXplore -- -r requirements.txt && npm run dist -- -w
rm -r GraphXplore/graphxplore