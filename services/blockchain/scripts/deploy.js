const hre = require("hardhat");

async function main() {
  const threatLog = await hre.ethers.deployContract("ThreatLog");

  await threatLog.waitForDeployment();

  console.log(`ThreatLog contract deployed to: ${threatLog.target}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

// Deployed to: 0x5FbDB2315678afecb367f032d93F642f64180aa3 (default)

