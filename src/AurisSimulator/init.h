// SPDX-FileCopyrightText: 2026 AURIS simulator contributors
// SPDX-License-Identifier: LGPL-2.1-or-later
#pragma once

#include <AurisSimulator/config.h>

namespace aurissimulator
{

/// Register the plugin in SOFA's PluginManager (safe to call several times).
AURISSIMULATOR_API void init();

} // namespace aurissimulator
