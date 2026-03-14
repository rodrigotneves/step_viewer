# Visualizador de STEP

Um aplicativo desktop desenvolvido em Python (PySide6 + PyVista + CadQuery) projetado para automatizar a busca, visualização 3D e extração de imagens de arquivos CAD no formato `.step` ou `.stp`. 

O sistema foi criado para facilitar a rotina de engenharia e manufatura, permitindo buscar dezenas de códigos de peças de uma só vez em diretórios de rede, validar a existência dos arquivos 3D e gerar *screenshots* isométricos em lote.

---

## 🚀 Funcionalidades

* **Busca em Lote Inteligente:** Permite colar uma lista de códigos de peças (Produtos/PGs ou Clientes) e localiza automaticamente os arquivos STEP correspondentes na rede, interpretando variações no formato do código.
* **Visualização 3D Avançada:** Renderização interativa da peça com iluminação (Lightkit), sombreamento suave (Smooth Shading) e anti-aliasing.
* **Automação de Prints (Batch Print):** Gera e salva automaticamente *screenshots* isométricos de todas as peças localizadas diretamente em uma pasta de destino na rede.
* **Auditoria de Arquivos:** Identifica rapidamente quais códigos não possuem arquivo 3D na rede e permite copiar a lista dos "não encontrados" para a área de transferência com um clique.
* **Carregamento Manual:** Opção para abrir e inspecionar visualmente qualquer arquivo STEP solto no computador local.

---

## ⚙️ Como Configurar

Antes de compilar ou rodar o projeto, é necessário ajustar os caminhos de rede hardcoded no arquivo `main.py` para refletirem a infraestrutura da sua empresa.

1. **Diretório Base de Busca:**
   No início do arquivo `main.py`, localize a variável `BASE_PATH` e insira o caminho da pasta raiz onde ficam os diretórios `CLIENTES` e `PRODUTOS`:
   ```python
   BASE_PATH = Path(r"\\servidor\departamento\desenhos")

2. Use como base, pois o código Regex é muito específico para o meu caso de uso, ele foi feito para encontrar os arquivos a partir do código de identificação do produto, um padrão só seguido na minha empresa, bem como os locais `CLIENTES` e `PRODUTOS`, são pastas origem desses produtos.