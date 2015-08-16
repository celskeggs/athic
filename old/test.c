#include "~ath.h"
void athmain() {
	AO stdout = import("ostream", "stdout");
	invoke(1, deref(stdout, "write"), (AO[]) {athstr("Hello, World.")});
	invoke(0, deref(aththis(), "DIE"), (AO[]) {});
}
