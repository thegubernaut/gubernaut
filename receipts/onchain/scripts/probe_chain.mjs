// Probe: does ganache boot on Node 26, and does an always-revert contract
// produce a real status:0 receipt with genuine gas burn? LOCAL DEVNET ONLY.
import ganache from "ganache";
import { createPublicClient, createWalletClient, http, defineChain } from "viem";

const PORT = 18545;
// init code that returns runtime `60006000fd` (PUSH1 0; PUSH1 0; REVERT):
// header `6005 80 600b 6000 39 6000 f3` (11 bytes) + runtime (5 bytes).
const ALWAYS_REVERT_INITCODE = "0x600580600b6000396000f360006000fd";

const devnet = defineChain({
  id: 31337,
  name: "gcc-local-devnet",
  nativeCurrency: { name: "Ether", symbol: "ETH", decimals: 18 },
  rpcUrls: { default: { http: [`http://127.0.0.1:${PORT}`] } },
});

async function main() {
  const server = ganache.server({
    chain: { chainId: 31337 },
    wallet: { deterministic: true, totalAccounts: 5 },
    miner: { blockGasLimit: "0x1c9c380" },
    logging: { quiet: true },
  });
  await server.listen(PORT);
  console.log(`ganache up on 127.0.0.1:${PORT}`);

  const pub = createPublicClient({ chain: devnet, transport: http() });
  const accounts = await pub.request({ method: "eth_accounts" });
  const from = accounts[0];
  const wallet = createWalletClient({ account: from, chain: devnet, transport: http() });

  const bal0 = await pub.getBalance({ address: from });

  // deploy
  const deployHash = await wallet.sendTransaction({ data: ALWAYS_REVERT_INITCODE, gas: 200000n });
  const deployRcpt = await pub.waitForTransactionReceipt({ hash: deployHash });
  const contract = deployRcpt.contractAddress;
  console.log(`deployed always-revert at ${contract} (deploy status ${deployRcpt.status})`);

  // send one call that must revert — explicit gas so viem skips estimation
  const txHash = await wallet.sendTransaction({ to: contract, data: "0xdeadbeef", gas: 100000n });
  const rcpt = await pub.waitForTransactionReceipt({ hash: txHash });
  const bal1 = await pub.getBalance({ address: from });

  console.log(`revert tx ${txHash}`);
  console.log(`  status=${rcpt.status}  gasUsed=${rcpt.gasUsed}  effGasPrice=${rcpt.effectiveGasPrice}`);
  console.log(`  balance ${bal0} -> ${bal1}  (drop ${bal0 - bal1} wei)`);
  console.log(`  nonce now = ${await pub.getTransactionCount({ address: from })}`);

  const ok = rcpt.status === "reverted" && bal1 < bal0;
  console.log(`PROBE ${ok ? "PASS" : "FAIL"} — real revert receipt + real gas drain`);
  await server.close();
  process.exit(ok ? 0 : 1);
}
main().catch((e) => { console.error("PROBE ERROR:", e); process.exit(2); });
