# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# SOFA plugin of the AURIS hybrid ear-surgery simulator (DC15).
# The C++ part is intentionally small: most of the simulator lives in the
# Python package `auris_sim` (python/). C++ components are added here only when
# they need to be fast or when SOFA does not provide them.

cmake_minimum_required(VERSION 3.22)
project(AurisSimulator VERSION 0.1.0 LANGUAGES CXX)

find_package(Sofa.Config REQUIRED)
sofa_find_package(Sofa.Core REQUIRED)

set(AURISSIMULATOR_SRC_DIR "src/${PROJECT_NAME}")

set(HEADER_FILES
    ${AURISSIMULATOR_SRC_DIR}/config.h.in
    ${AURISSIMULATOR_SRC_DIR}/init.h
)

set(SOURCE_FILES
    ${AURISSIMULATOR_SRC_DIR}/init.cpp
)

set(README_FILES
    README.md
)

add_library(${PROJECT_NAME} SHARED ${HEADER_FILES} ${SOURCE_FILES} ${README_FILES})
target_link_libraries(${PROJECT_NAME} PUBLIC Sofa.Core)

sofa_create_package_with_targets(
    PACKAGE_NAME ${PROJECT_NAME}
    PACKAGE_VERSION ${PROJECT_VERSION}
    TARGETS ${PROJECT_NAME} AUTO_SET_TARGET_PROPERTIES
    INCLUDE_SOURCE_DIR "src"
    INCLUDE_INSTALL_DIR ${PROJECT_NAME}
    RELOCATABLE "plugins"
)
