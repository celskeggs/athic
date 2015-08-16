#include "~ath.h"
#include <stdlib.h>

AO import_ostream(const char *name) {
	if (!strcmp(name, "stdout")) {
		return (AO) {A_OSTREAM, {.fptr = stdout}};
	} else if (!strcmp(name, "stderr")) {
		return (AO) {A_OSTREAM, {.fptr = stderr}};
	} else {
		return athnull();
	}
}

AO ostream_write(int acount, AO bound, AO* args) {
	if (acount != 1 || !(args[0].type == A_CONST_STRING || args[0].type == A_DYN_STRING)) {
		return athnull();
	} else {
		return athint(fputs(args[0].value.string, bound.value.fptr));
	}
}

AO this_die(int acount, AO bound, AO* args) {
	if (acount == 1 && args[0].type == A_INTEGER) {
		exit(args[0].value.integer);
	} else {
		exit(0);
	}
	return athnull();
}

AO import(const char *type, const char *name) {
	if (!strcmp(type, "ostream")) {
		return import_ostream(name);
	} else {
		return athnull();
	}
}

AO athint(int x) {
	return (AO) {A_INTEGER, {.integer=x}};
}
AO athstr(const char *value) {
	return (AO) {A_CONST_STRING, {.string=value}};
}
AO athmethod(AO *bound, mptr method) {
	return (AO) {A_METHOD, {.method={bound, method}}};
}
AO aththis() {
	return (AO) {A_THIS};
}
AO athnull() {
	return (AO) {A_NULL};
}

AO deref(AO *obj, const char *name) {
	switch (obj->type) {
	case A_OSTREAM:
		if (!strcmp(name, "write")) {
			return athmethod(obj, ostream_write);
		}
		return (AO) {A_NULL};
	case A_THIS:
		if (!strcmp(name, "DIE")) {
			return athmethod(obj, this_die);
		}
		return (AO) {A_NULL};
	case A_NULL:
	case A_INTEGER:
	case A_CONST_STRING:
	case A_DYN_STRING:
	case A_METHOD:
	default:
		return (AO) {A_NULL};
	}
}

AO invoke(int acount, AO obj, AO args[]) {
	if (obj.type == A_METHOD) {
		return obj.value.method.ptr(acount, obj.value.method.bound, args);
	} else {
		return (AO) {A_NULL};
	}
}
