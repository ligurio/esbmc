add_library(luafrontend STATIC lua_language.cpp)

target_include_directories(luafrontend
    PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}
)
