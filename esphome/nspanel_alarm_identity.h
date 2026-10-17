#pragma once
#include <string>
namespace wake_alarm {
// Prevent a valid API call routed to the wrong panel from changing its plan.
// Transport authentication is still provided by the encrypted ESPHome API.
inline bool matches_identity(const std::string &expected_name,
    const std::string &expected_mac, const std::string &actual_name,
    const std::string &actual_mac) {
  return !expected_name.empty() && !expected_mac.empty() &&
         expected_name == actual_name && expected_mac == actual_mac;
}
}
