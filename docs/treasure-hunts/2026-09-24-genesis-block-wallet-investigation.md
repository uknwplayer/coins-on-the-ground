# Genesis Block Wallet Puzzle — investigação de 2026-09-24

## Status

Alvo público e explicitamente autorizado:

```text
bc1qfkhx02v89u2qyyyljeczw6hu9sr437y44t7ae5yf09thrdukfqesnjg2wj
```

Anúncio original:

- tx: `b691de3657880d9a1eabd2783b1a9fa8c5313ced338495bf10e85727012d7a77`
- block: `963629`
- texto do autor: puzzle criado com informação do genesis block, baixa entropia e convite público para resolver.

Fontes de pesquisa:

- https://github.com/floflo777/open-crypto-puzzles/tree/main/3-small-prizes/genesis-block-wallet-puzzle-142ksats
- https://puzzles.agntn.dev/collections/genesis
- https://ra0.org/
- https://mempool.space/address/bc1qfkhx02v89u2qyyyljeczw6hu9sr437y44t7ae5yf09thrdukfqesnjg2wj

Em 2026-09-24, a página do endereço no mempool.space mostrou:

```text
confirmed balance: 0.00412298 BTC
confirmed UTXOs: 51
total received/funded: 0.00412298 BTC
transaction count: 51
```

O valor é dinâmico porque pagamentos por hints são adicionados ao endereço.

## Modelo estabelecido antes deste bloco

As pistas públicas já estabeleciam:

1. P2WSH 2-of-2 multisig;
2. duas chaves, ambas obrigatórias;
3. ambas usam o mesmo campo/dado do Genesis e são derivadas independentemente;
4. BIP48, com ordem indicada pelo autor como:
   `root -> multisig -> mainnet -> genesis_data -> script_type`;
5. root = master key derivada de BIP39;
6. BIP39 com 12 palavras;
7. existe passphrase;
8. `genesis_data` entra como account number no BIP48.

O target witness program usado para comparação offline é:

```text
4dae67a9872f1402109f9670276afc2c0758f895aafddcd089795771b7964833
```

Script testado:

```text
OP_2 <compressed_pubkey_A> <compressed_pubkey_B> OP_2 OP_CHECKMULTISIG
```

As duas ordens das pubkeys são comparadas.

## Pistas novas posteriores ao snapshot antigo

O catálogo @agntn/puzzles registra pistas posteriores que estreitam o problema:

- a passphrase é um **nome**;
- quando perguntado sobre a passphrase, o autor respondeu com a pergunta:
  `Who received the first transaction?`;
- isso aponta fortemente para **Hal Finney**, embora o formato textual continue propositalmente não revelado;
- a entropia **não** é simplesmente um bloco cru de 16 bytes;
- o autor a descreveu como um **digest de 128 bits**;
- uma resposta posterior diz que o formato da passphrase precisa ser descoberto por brute force.

Em bloco `968172`, foi publicada a pergunta:

```text
Which block part + which hash gives the 128-bit entropy? One line.
```

Em bloco `968343`, tx:

```text
ae906bdebdf7cd2e9b2490a727d5d91eaa203c2ae68f8461ea62e07ffe3b9b1c
```

apareceu a resposta:

```text
First 128 bits of SHA-256 hash of the genesis block's entropy.
Encrypted pubkey: 50k sats output + 1k input.
```

Essa mensagem usa como input o endereço `bc1qyas2lnfgzjh3lyl4vfhc68daedc890zn8yetaj`, o mesmo endereço-fonte observado no financiamento/anúncio inicial do puzzle. Isso é um sinal forte de continuidade de controle, embora a atribuição continue sendo tratada como evidência on-chain, não identidade pessoal.

### Contradição preservada

Uma pista antiga dizia `there is no hash`, enquanto as mais novas explicitamente falam em SHA-256.

Não vamos apagar essa inconsistência para tornar a hipótese mais bonita. Ela pode significar:

- a frase antiga se referia apenas a uma etapa específica da derivação;
- o autor mudou/clarificou a terminologia;
- ou ainda interpretamos uma das respostas de forma errada.

## Implementação local

Foi implementado um verificador offline independente com:

- wordlist oficial BIP39 English;
- checksum e geração de mnemonic de 12 palavras a partir de 128 bits;
- PBKDF2-HMAC-SHA512 BIP39;
- master/child private derivation BIP32;
- secp256k1;
- BIP48 `m/48'/0'/account'/2'`;
- suffixes de endereço/cadeia candidatos;
- reconstrução exata do witness script P2WSH;
- SHA-256 e comparação byte a byte com o target.

Nenhuma chave privada candidata foi publicada ou enviada a terceiros.

## Teste A — leitura mais natural

Campos de entrada para SHA-256:

```text
coinbase_text
headline
scriptSig
The Times date prefix
whole genesis block (285 bytes)
```

Passphrases:

- 15 variantes naturais de `Hal Finney`, `Hal`, `Finney` e `Harold Finney`.

Accounts principais:

```text
0
50
2009
486604799   # bits
1231006505  # timestamp
2083236893  # nonce
```

Para cada campo:

- SHA-256;
- primeiros 128 bits como entropy BIP39;
- também segunda metade do digest como hipótese para um segundo root independente;
- BIP48;
- suffixes `[]`, `/0/0`, `/0/1`, `/1/0`;
- modelos de duas chaves:
  - mesmo root + child keys diferentes;
  - first128 + last128 como dois roots independentes.

Resultado:

```text
21,600 script checks
NO MATCH
elapsed: 6.56 s
```

## Teste B — representações binárias do bloco

Campos:

```text
80-byte block header
whole 285-byte genesis block
205-byte coinbase transaction
65-byte coinbase public key
merkle root wire bytes
displayed block hash bytes
```

Mesmo conjunto principal de passphrase/account/suffix.

Resultado:

```text
25,920 script checks
NO MATCH
elapsed: 8.14 s
```

## Teste C — passphrases cruzadas

O teste anterior supunha a mesma passphrase para os dois lados.

Foi então testado um conjunto cruzado com:

- 10 campos Genesis prioritários;
- 23 formatos de nome;
- variantes de Hal Finney;
- variantes de Satoshi Nakamoto como controle;
- first128 e last128 do SHA-256;
- seis account numbers principais;
- quatro suffixes BIP48.

Qualquer pubkey candidata pôde ser combinada com outra do mesmo campo/account, inclusive:

- passphrases diferentes;
- primeira/segunda metade do digest;
- suffixes diferentes.

Resultado:

```text
2,020,320 exact witness-script checks
NO MATCH
elapsed: 21.2 s
```

## O que foi eliminado

Este bloco torna menos prováveis:

1. `SHA256(coinbase text)[:16]` + formas óbvias de Hal Finney;
2. o mesmo usando headline, scriptSig, header, bloco inteiro, coinbase tx, pubkey, merkle e block hash;
3. first/last halves do mesmo digest como os dois cosigner roots;
4. mesma mnemonic com dois child indexes comuns;
5. combinações cruzadas de Hal/Satoshi como passphrases nos caminhos testados.

O resultado negativo é apenas para o espaço explicitamente listado. Não prova que essas entidades nunca apareçam numa construção diferente.

## Próximas hipóteses

A maior incerteza agora não é mais "BIP39 ou não". É:

```text
qual representação exata o autor chama de "the genesis block's entropy"?
```

Próximos testes de maior retorno:

1. representações textuais/hex/endianness adicionais do mesmo campo;
2. dupla interpretação da palavra `entropy` antes do SHA-256;
3. account number menos óbvio derivado do mesmo campo;
4. dois roots construídos por uma regra independente ainda não modelada;
5. observar novos OP_RETURNs antes de aumentar o brute force.

## Restrições operacionais

Nenhum satoshi foi enviado neste bloco.

Não vamos comprar hint ou o "encrypted pubkey" sem autorização explícita para gasto.

Se uma solução produzir material privado válido, esse segredo **não deve ser commitado no GitHub**.
Primeiro deve ser validado localmente e usado por uma rota de claim segura.
