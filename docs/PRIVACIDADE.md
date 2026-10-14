# Privacidade e proteção de dados pessoais (LGPD)

## Inventário
| Informação | Existe hoje? | Detalhe |
|---|---|---|
| Dados de pacientes ou profissionais | **Não** | Os relatórios do Siaps usados são agregados por município/equipe (contagens). |
| Contas de usuário, e-mail, senha | **Não** | O painel não tem login. |
| Registros de acesso (logs) | Parcial | `logs/siaps.log` local registra execuções da coleta (horário, quadrimestres, erros); **sem** IP de terceiros, nome ou dados clínicos. O servidor local registra IP `127.0.0.1`. |
| Texto livre do plano de ação | **Possível** | Campos “Ação planejada” e “Setor responsável”. Ficam **só no navegador** do usuário (`localStorage`); não são enviados a servidor algum. |
| Cookies / rastreadores / analytics | **Não** | Nenhum; sem scripts de terceiros em tempo de execução. |

## Finalidade, acesso, retenção e descarte
- **Finalidade:** apoiar a gestão da APS de Pacujá (monitoramento de qualidade e planejamento de ações).
- **Acesso:** o plano de ação só é visível a quem usa aquele navegador/perfil do computador.
- **Retenção:** dados oficiais agregados — permanente (histórico); plano de ação — até o usuário usar “Limpar plano” ou
  apagar os dados do navegador; logs — rotação automática (4 arquivos de 500 KB).
- **Descarte:** botão “Limpar plano deste quadrimestre”; apagar `logs/`; os dados agregados não exigem descarte.

## Regras de uso (exibidas no painel)
- **Não** escrever nomes de pessoas, CPF, CNS, prontuário, diagnósticos ou qualquer informação clínica identificável
  nos campos livres. Informar **setor/cargo**, não a pessoa.
- Exportações CSV do plano contêm o texto digitado: tratar o arquivo conforme a política interna da Secretaria.

## Se o escopo crescer
Plano compartilhado, contas ou registro de acesso por usuário implicam dados pessoais: antes, definir **base legal e
finalidade**, nomear controlador e encarregado (DPO), registrar operações de tratamento, avaliar a necessidade de RIPD e
seguir as orientações da ANPD ([guia de segurança da informação para agentes de tratamento de pequeno porte](https://www.gov.br/anpd/pt-br)).
Este documento é um inventário técnico, **não** parecer jurídico: a Secretaria deve validar com seu encarregado.
