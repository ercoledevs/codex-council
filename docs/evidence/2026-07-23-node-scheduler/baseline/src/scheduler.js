"use strict";

async function runJobs(jobs, worker) {
  if (!Array.isArray(jobs)) {
    throw new TypeError("jobs must be an array");
  }
  if (typeof worker !== "function") {
    throw new TypeError("worker must be a function");
  }

  const results = [];
  for (let index = 0; index < jobs.length; index += 1) {
    try {
      const value = await worker(jobs[index], index);
      results.push({ status: "fulfilled", value });
    } catch (error) {
      results.push({
        status: "rejected",
        reason: error instanceof Error ? error.message : String(error),
      });
    }
  }
  return results;
}

module.exports = { runJobs };
