// Inventory helpers for the probe fixture.
#include <map>
#include <string>
#include <stdexcept>

int restock(std::map<std::string, int>& counts, const std::string& sku, int n) {
    if (n < 0) { throw std::invalid_argument("negative restock"); }
    counts[sku] += n;
    return counts[sku];
}
