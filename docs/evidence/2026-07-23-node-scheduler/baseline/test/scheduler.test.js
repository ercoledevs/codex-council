"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { runJobs } = require("../src/scheduler");

test("runs jobs in input order", async () => {
  const calls = [];
  const result = await runJobs(["a", "b", "c"], async (job, index) => {
    calls.push([job, index]);
    return job.toUpperCase();
  });

  assert.deepEqual(calls, [["a", 0], ["b", 1], ["c", 2]]);
  assert.deepEqual(result, [
    { status: "fulfilled", value: "A" },
    { status: "fulfilled", value: "B" },
    { status: "fulfilled", value: "C" },
  ]);
});

test("captures worker failures without stopping later jobs", async () => {
  const result = await runJobs([1, 2, 3], async (job) => {
    if (job === 2) throw new Error("boom");
    return job * 10;
  });

  assert.deepEqual(result, [
    { status: "fulfilled", value: 10 },
    { status: "rejected", reason: "boom" },
    { status: "fulfilled", value: 30 },
  ]);
});

test("validates arguments", async () => {
  await assert.rejects(() => runJobs(null, async () => {}), /jobs must be an array/);
  await assert.rejects(() => runJobs([], null), /worker must be a function/);
});
