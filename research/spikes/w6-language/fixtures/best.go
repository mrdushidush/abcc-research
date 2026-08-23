// Package inventory holds helpers for the probe fixture.
package inventory

import "errors"

// Restock adds n units of sku, refusing negative quantities.
func Restock(counts map[string]int, sku string, n int) (int, error) {
	if n < 0 {
		return 0, errors.New("negative restock")
	}
	counts[sku] += n
	return counts[sku], nil
}

// TestRestock covers the happy path.
func TestRestock(t *testing.T) {
	c := map[string]int{}
	got, err := Restock(c, "a", 2)
	if err != nil {
		t.Fatal(err)
	}
	if got != 2 {
		t.Fatalf("got %d", got)
	}
}
