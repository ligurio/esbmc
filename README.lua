cmake -S . -B build -DENABLE_PYTHON_FRONTEND=ON -DENABLE_LUA_FRONTEND=ON -DBUILD_TESTING=ON -DENABLE_Z3=ON

https://github.com/stevenjohnstone/lua-grammar/tree/master

### Generate Lua parser and lexer

```
sudo apt-get install antlr4
curl -O -L http://www.antlr.org/download/antlr-4.9.2-complete.jar
```

https://github.com/antlr/antlr4/blob/4.9.1/runtime/Cpp/cmake/Antlr4Package.md
https://tomassetti.me/getting-started-antlr-cpp/
https://github.com/antlr/antlr4/tree/master/runtime/Cpp
https://github.com/antlr/antlr4/blob/master/doc/cpp-target.md
