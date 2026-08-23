# Inventory helpers for the probe fixture.
def restock(counts, sku, n)
  raise ArgumentError, 'negative restock' if n.negative?

  counts[sku] = counts.fetch(sku, 0) + n
rescue TypeError => e
  raise ArgumentError, 'bad counts', e.backtrace
end

def test_restock
  raise unless restock({}, 'a', 2) == { 'a' => 2 }
end
