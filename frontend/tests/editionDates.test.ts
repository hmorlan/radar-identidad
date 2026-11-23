import assert from 'node:assert/strict';
import { test } from 'node:test';
import { shortDate } from '../src/lib/components/edition/editionUtils.ts';

// 23 nov: la nota I (BleepingComputer, 21 nov 18:01 UTC) salía "22 nov" en CDMX.
test('la fecha de la nota no se corre por la zona horaria', () => {
	assert.equal(shortDate('2026-11-21T18:01:58'), '21 nov 2026');
	assert.equal(shortDate('2026-11-20T22:33:55'), '20 nov 2026');
	assert.equal(shortDate('2026-11-21'), '21 nov 2026');
	assert.equal(shortDate('2026-01-05T00:30:00Z'), '5 ene 2026');
});

test('fechas vacías o inválidas no rompen la nota', () => {
	assert.equal(shortDate(''), '');
	assert.equal(shortDate(null), '');
	assert.equal(shortDate('2026-13-01'), '');
	assert.equal(shortDate('ayer'), '');
});
