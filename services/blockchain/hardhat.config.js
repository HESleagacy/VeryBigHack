require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config({ path: '../../.env' });

module.exports = {
  solidity: {
    compilers: [
      {
        version: "0.8.24",
        settings: {}
      }
    ]
  },
  networks: {
    hardhat: {
      chainId: 1337
    }
  },
  defaultNetwork: "hardhat",
};

