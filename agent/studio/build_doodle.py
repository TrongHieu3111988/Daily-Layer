s=open("doodle_app.html").read(); core=open("doodle_core.js").read()
for name,url in [("doodle_artifact.html","https://claude.ai/artifact/NWvKP3j5tXF8mCmxkDrE4A"),("doodle_standalone.html","/")]:
    body=s.replace("/*DOODLE*/",core).replace('<script>\n"use strict";','<script>\nwindow.SHOP_URL = "'+url+'";\n"use strict";',1)
    if name=="doodle_standalone.html":
        title,rest=body.split("\n",1)
        body=("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">\n"
              "<meta name=\"description\" content=\"Kids draw an animal or any shape, and it puffs up into a 3D model you can print.\">\n"+title+"\n"
              +rest.replace('<meta name="claude:viewport-fit-sides" content="cover">\n','').replace('<div class="app">','</head>\n<body>\n<div class="app">',1))
        body=body.replace("*{box-sizing:border-box}","*{box-sizing:border-box}\nbody{margin:0}[hidden]{display:none!important}\n:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}",1)
        body=body.rstrip()+"\n</body>\n</html>\n"
    open(name,"w").write(body)
print("built")
