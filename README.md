# Organizador de Arquivos CLI

CLI em **Python 3.11**, sem dependências de runtime, para organizar uma pasta por extensão e categoria. O projeto prioriza operação segura: oferece `--dry-run`, registra logs, trata falhas por arquivo, evita links simbólicos e é idempotente.

## Recursos

- Categorias padrão para imagens, documentos, planilhas, apresentações, vídeos, áudios, compactados e código.
- Extensões comparadas sem distinção entre maiúsculas e minúsculas (`.JPG` e `.jpg` têm o mesmo destino).
- Arquivos sem extensão ou com extensão desconhecida vão para `Outros`.
- Modo `--dry-run`: calcula o plano sem criar pastas nem mover arquivos.
- Estratégias de conflito: `rename` (padrão, cria `arquivo (1).ext`), `skip` ou `overwrite`.
- Modo recursivo opcional; pastas de categoria já existentes não são percorridas novamente.
- Arquivos e diretórios ocultos são ignorados por padrão.
- Links simbólicos nunca são seguidos.
- Logs no terminal e opcionalmente em arquivo.
- Configuração JSON validada, testes `unittest` e CI no GitHub Actions.
- Execuções repetidas não movem novamente os arquivos já organizados.

## Instalação

Requer Python 3.11 ou superior. Para instalar localmente:

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

Também é possível executar sem instalar:

```bash
python -m organizador_arquivos /caminho/da/pasta --dry-run
```

## Uso

Sempre faça uma simulação antes da primeira execução:

```bash
organizar-arquivos ~/Downloads --dry-run --verbose
```

Depois execute de fato:

```bash
organizar-arquivos ~/Downloads --log-file ~/organizador.log
```

Opções principais:

```text
organizar-arquivos [PASTA] [--config ARQUIVO] [--dry-run]
                   [--recursive] [--include-hidden]
                   [--conflict-strategy {rename,skip,overwrite}]
                   [--log-file ARQUIVO] [--json] [-v] [--version]
```

`--json` emite o resumo completo, útil em scripts:

```bash
organizar-arquivos ./entrada --dry-run --json > plano.json
```

### Códigos de saída

- `0`: operação concluída sem erros (inclui `--dry-run`).
- `1`: a operação terminou, mas uma ou mais movimentações falharam.
- `2`: erro fatal de configuração, caminho de origem ou abertura do log.

## Configuração JSON

Passe um arquivo com `--config`. Todas as chaves são opcionais; se `categories` não for informada, as categorias padrão são usadas. Exemplo:

```json
{
  "categories": {
    "Fotos": [".jpg", "jpeg", ".png", ".heic"],
    "Textos": [".txt", ".md", ".pdf"],
    "Projetos": [".py", ".js", ".toml"]
  },
  "unknown_category": "Outros",
  "recursive": true,
  "include_hidden": false,
  "conflict_strategy": "rename",
  "ignore": [".git", "node_modules", "venv"]
}
```

As extensões podem ser escritas com ou sem ponto e são normalizadas para minúsculas. Uma extensão não pode pertencer a duas categorias. Nomes de categoria são usados como nomes de diretório e, por segurança, não podem conter `/`, `\\`, quebras de linha, `.` ou `..`.

### Estratégias de conflito

- `rename`: preserva o arquivo existente e gera nomes incrementais (`relatorio (1).pdf`, `relatorio (2).pdf`).
- `skip`: deixa o arquivo na origem e contabiliza-o como ignorado.
- `overwrite`: substitui o destino existente. Use somente quando isso for intencional.

## Estrutura gerada

```text
pasta/
├── Imagens/
├── Documentos/
├── Planilhas/
├── ...
└── Outros/
```

No modo recursivo, o arquivo permanece no nível da pasta onde foi encontrado e a categoria é criada nesse nível. Pastas que já têm nome de categoria são excluídas do percurso, o que evita reprocessamento.

## Desenvolvimento e testes

O projeto usa apenas a biblioteca padrão. Para executar todos os testes:

```bash
python -m unittest discover -s tests -v
```

Para verificar compilação:

```bash
python -m compileall -q organizador_arquivos tests
```

A automação em `.github/workflows/ci.yml` instala o pacote, executa `unittest` e verifica a compilação em Python 3.11.

## Segurança e limitações

- O programa **move** arquivos; ele não faz cópia de segurança automática. Faça backup quando os dados forem importantes.
- Comece sempre com `--dry-run` e revise o resumo.
- Links simbólicos e arquivos ocultos são ignorados por padrão para evitar alterações inesperadas.
- Erros de uma entrada são registrados e não interrompem entradas independentes; o código `1` sinaliza que é necessária revisão.

## Licença

Distribuído sob a [Licença MIT](LICENSE).
