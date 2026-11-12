// SPDX-FileCopyrightText: 2026 AURIS simulator contributors
// SPDX-License-Identifier: LGPL-2.1-or-later
#include <AurisSimulator/init.h>

#include <sofa/core/ObjectFactory.h>
#include <sofa/helper/system/PluginManager.h>

namespace aurissimulator
{

// Declare here the registration function of each C++ component, e.g.
//   extern void registerInsertionForceMonitor(sofa::core::ObjectFactory* factory);

extern "C" {
    AURISSIMULATOR_API void initExternalModule();
    AURISSIMULATOR_API const char* getModuleName();
    AURISSIMULATOR_API const char* getModuleVersion();
    AURISSIMULATOR_API const char* getModuleLicense();
    AURISSIMULATOR_API const char* getModuleDescription();
    AURISSIMULATOR_API void registerObjects(sofa::core::ObjectFactory* factory);
}

void init()
{
    static bool first = true;
    if (first)
    {
        sofa::helper::system::PluginManager::getInstance().registerPlugin(MODULE_NAME);
        first = false;
    }
}

void initExternalModule()
{
    init();
}

const char* getModuleName()
{
    return MODULE_NAME;
}

const char* getModuleVersion()
{
    return MODULE_VERSION;
}

const char* getModuleLicense()
{
    return "LGPL-2.1-or-later";
}

const char* getModuleDescription()
{
    return "AURIS hybrid ear-surgery simulator (DC15 of the AURIS MSCA Doctoral Network).";
}

void registerObjects(sofa::core::ObjectFactory* /*factory*/)
{
    // No C++ component yet. Call the registration functions declared above, e.g.
    //   registerInsertionForceMonitor(factory);
}

} // namespace aurissimulator
