# Distributed under the MIT License. See LICENSE for details.

#add_subdirectory(DataStructures)
#add_subdirectory(ErrorHandling)
#add_library(${PROJECT_NAME}::ErrorHandling ALIAS ErrorHandling)

add_subdirectory(ModuleSettings)
add_library(${PROJECT_NAME}::ModuleSettings ALIAS ModuleSettings)

#add_subdirectory(Options)
#add_library(${PROJECT_NAME}::Options ALIAS Options)

#add_subdirectory(Parallel)
#add_library(${PROJECT_NAME}::Parallel ALIAS Parallel)

#add_subdirectory(PythonBindings)
#if (${ELASTICA_BUILD_PYTHON_BINDINGS})
#    add_library(${PROJECT_NAME}::PythonBindings ALIAS PythonBindings)
#endif ()

#add_subdirectory(Simulator)
#add_library(${PROJECT_NAME}::Simulator ALIAS Simulator)

add_subdirectory(Systems)
add_library(${PROJECT_NAME}::Systems ALIAS Systems)

#add_subdirectory(Time)
#add_library(${PROJECT_NAME}::Time ALIAS Time)

add_subdirectory(Utilities)
add_library(${PROJECT_NAME}::Utilities ALIAS Utilities)

add_library(${PROJECT_NAME} INTERFACE)
target_include_directories(${PROJECT_NAME} INTERFACE
        $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}>
        $<BUILD_INTERFACE:${PROJECT_BINARY_DIR}>
        $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)

set(ELASTICA_TOPLEVEL_LIBS
        "ModuleSettings;Systems;Utilities")
#"ErrorHandling;ModuleSettings;Options;Parallel;Simulator;Systems;Time;Utilities")

foreach (ELASTICA_LIB ${ELASTICA_TOPLEVEL_LIBS})
    target_link_libraries(${PROJECT_NAME}
            INTERFACE
            ${ELASTICA_LIB}
            )
endforeach (ELASTICA_LIB ${ELASTICA_TOPLEVEL_LIBS})

# set to global
set_property(GLOBAL PROPERTY ELASTICA_TOPLEVEL_LIBS_PROPERTY ${ELASTICA_TOPLEVEL_LIBS})
unset(ELASTICA_TOPLEVEL_LIBS)
