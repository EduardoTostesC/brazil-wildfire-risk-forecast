"""Render the actual publication commits, including the current CI checkout."""

import argparse
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "5877c8ab1e84443a7d9671fb7f6af13ae0fc3792"
VALIDATION = {
    "chore(release)": ("Preparar branch e contratos de integração", "Bundle/protocolo conferidos; CI release/** habilitado", "reports/ESTADO_PRE_PUBLICACAO.md"),
    "feat(dashboard)": ("Interface bilíngue e gráficos responsivos", "6 testes; 20 combinações de navegador e 2 falhas de carregamento", "reports/DASHBOARD_FINAL.md"),
    "perf(serving)": ("Distribuição runtime com hashes e paridade", "110 testes locais; CI 40439513994 verde; 54 pares HTTP e 6 erros", "docs/DEPLOY_RETROSPECTIVO.md"),
    "test(performance)": ("Medir latência, CPU e memória de processos reais", "2826 requisições válidas; zero erros HTTP; raw CSV/JSON preservados", "reports/BENCHMARKS_SERVING.md"),
    "feat(data)": ("Aquisição imutável, verificações de unidade e hashes", "8 testes; POWER real com 3 dias de 2024", "reports/REPRODUCAO_PUBLICA_STATUS.md"),
    "feat(research)": ("Executor somente de avaliação e gates pré-desfechos", "24 testes técnicos; baselines originais equivalentes; nenhuma avaliação 2027", "reports/EXECUTOR_CONFIRMATORIO_STATUS.md"),
    "docs(release)": ("Documentação, metadados e release candidata", "Geradores/links e verificações finais documentados; sem publicação automática", "reports/FINALIZACAO_PUBLICACAO.md"),
    "test(release)": ("Preservar evidências e fechamento", "Logs locais/clone e checks do SHA no workflow; consultar conclusão remota", "reports/FINALIZACAO_PUBLICACAO.md"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/COMMITS_PROXIMA_FASE.md")
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    def git(*arguments):
        return subprocess.check_output(["git", *arguments], cwd=ROOT, encoding="utf-8").strip()
    commits = []
    for sha in git("rev-list", "--reverse", BASE + "..HEAD").splitlines():
        message = git("show", "-s", "--format=%s", sha)
        files = git("diff-tree", "--no-commit-id", "--name-only", "-r", sha).splitlines()
        prefix = message.split(":", 1)[0]
        objective, checks, evidence = VALIDATION.get(prefix, ("Correção de revisão crítica", "Consultar evidência no fechamento e checks do SHA", "reports/FINALIZACAO_PUBLICACAO.md"))
        commits.append(dict(sha=sha, message=message, files=files, objective=objective, checks=checks, evidence=evidence))
    workflow = None
    if os.environ.get("GITHUB_RUN_ID"):
        workflow = f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    lines = ["# Commits da próxima fase", "", f"Base preservada: `{BASE}`. Checkout inventariado: `{git('rev-parse', 'HEAD')}`.", "",
        "Inventário gerado do Git real. O relatório versionado lista os commits existentes antes de seu fechamento; o próprio commit que o grava aparece no inventário completo do artefato CI e em git log. Isso evita inventar o SHA de um commit que ainda não existia.", ""]
    if workflow:
        lines += [f"Workflow deste checkout: {workflow}. A existência deste inventário não antecipa a conclusão do job Docker; conferir os checks remotos.", ""]
    for entry in commits:
        lines += [f"## {entry['sha']}", "", entry["message"], "", f"Objetivo: {entry['objective']}.",
                  f"Verificação: {entry['checks']}.", f"Evidência: {entry['evidence']}.",
                  "Arquivos: " + ", ".join("`" + name + "`" for name in entry["files"]) + ".", ""]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    if args.json:
        args.json.write_text(json.dumps({"base": BASE, "head": git("rev-parse", "HEAD"), "workflow": workflow, "commits": commits}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Recorded {len(commits)} real commits")


if __name__ == "__main__":
    main()
