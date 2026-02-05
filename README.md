# Paradox Serial Interface

Interface Python simplificada para comunicação com centrais de alarme Paradox (MG/SP/Digiplex) via porta serial TTL.

Este projeto é baseado na engenharia reversa do excelente projeto [ParadoxAlarmInterface/pai](https://github.com/ParadoxAlarmInterface/pai) e tem como objetivo servir de base para estudos e posterior implementação em microcontroladores STM32F411.

## 🎯 Objetivos

- Criar um protótipo em Python para testes de comunicação serial com centrais Paradox
- Implementar protocolo de comunicação baseado em engenharia reversa
- Fornecer base de código simples e educativa para porte futuro para C/STM32
- Desenvolver alternativa ao módulo IP150 usando Ethernet + microcontrolador

## 📋 Compatibilidade

### Painéis Suportados

- **Magellan Series**: MG5000, MG5050
- **Spectra Series**: SP4000, SP5500, SP6000, SP7000, SP65
- **Digiplex Series**: DGP2 (vários modelos)

### ⚠️ Limitações Importantes

- **Firmware < 7.50**: Este projeto funciona apenas com firmware anterior à versão 7.50
- **Firmware 7.50+**: Introduz criptografia no protocolo, não suportada nesta implementação
- **Verificação**: Consulte versão do firmware no Babyware ou no painel

## 🔧 Requisitos de Hardware

### Componentes Necessários

1. **Conversor USB-TTL** (exemplo: FTDI FT232RL, CH340)
2. **Level Shifter 5V ↔ 3.3V** (conversor bidirecional de nível lógico)
3. **Cabos de conexão**
4. **Central Paradox** compatível

### Diagrama de Conexão

```
PC USB ←→ Conversor USB-TTL ←→ Level Shifter ←→ Central Paradox
          (3.3V)                 (5V ↔ 3.3V)        (5V TTL)
                                                     
Conversor USB-TTL          Level Shifter         Central Paradox
┌──────────────┐          ┌────────────┐         ┌──────────────┐
│ 3.3V    (VCC)│────────→ │ LV   ↔  HV │←────────│ +5V (AUX+)   │
│ GND     (GND)│────────→ │ GND     GND│←────────│ GND (AUX-)   │
│ TX      (TXD)│────────→ │ TX1  ↔  TX2│←────────│ SERIAL IN    │
│ RX      (RXD)│←────────→│ RX1  ↔  RX2│←────────│ SERIAL OUT   │
└──────────────┘          └────────────┘         └──────────────┘
```

### ⚠️ Avisos de Segurança

- **NUNCA conecte 5V diretamente ao conversor USB-TTL 3.3V** - use level shifter!
- Desligue a central antes de fazer conexões
- Verifique polaridade de alimentação
- Use alimentação estabilizada

### Pinos da Central Paradox

Consulte o manual da sua central para localizar:
- **AUX+**: +5V (vermelho)
- **AUX-**: GND (preto)
- **SERIAL IN**: Entrada serial (verde)
- **SERIAL OUT**: Saída serial (amarelo)

## 💻 Instalação

### Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)
- Permissões para acessar porta serial (Linux: grupo `dialout`)

### Linux

```bash
# Clone o repositório
git clone https://github.com/MarceloAri/paradox-serial-interface.git
cd paradox-serial-interface

# Instale dependências
pip install -r requirements.txt

# Adicione usuário ao grupo dialout (necessário para acessar porta serial)
sudo usermod -a -G dialout $USER
# IMPORTANTE: Faça logout e login novamente para aplicar

# Ou execute com sudo
sudo python3 main.py
```

### Windows

```bash
# Clone o repositório
git clone https://github.com/MarceloAri/paradox-serial-interface.git
cd paradox-serial-interface

# Instale dependências
pip install -r requirements.txt

# Execute
python main.py
```

## ⚙️ Configuração

### 1. Senha PC (Password PC)

A senha PC deve ser configurada no software **Babyware** (software de programação Paradox):

1. Conecte ao painel via Babyware
2. Navegue até: **System Options → Communication**
3. Localize **PC Password** (4 dígitos hexadecimais: 0-9, a-f)
4. Anote a senha para usar no arquivo de configuração

**Padrão de fábrica**: Geralmente `0000` ou `AAAA`

### 2. Arquivo config.yaml

Edite o arquivo `config.yaml` com suas configurações:

```yaml
serial:
  port: "/dev/ttyUSB0"  # Windows: "COM3", Linux: "/dev/ttyUSB0"
  baudrate: 9600        # 9600 baud (padrão Paradox)
  timeout: 5            # Timeout em segundos

panel:
  pc_password: "0000"   # Senha PC (4 dígitos hex: 0-9a-f)
  model: "MG5050"       # Modelo do painel

logging:
  level: "DEBUG"        # DEBUG, INFO, WARNING, ERROR
  dump_packets: true    # Log de pacotes em hexadecimal
```

### 3. Identificar Porta Serial

**Linux:**
```bash
# Liste portas USB
ls -l /dev/ttyUSB*
# ou
dmesg | grep tty

# Teste de permissões
python3 -m serial.tools.list_ports
```

**Windows:**
```
# Abra Gerenciador de Dispositivos
# Procure em "Portas (COM e LPT)"
# Anote a porta COM (ex: COM3)
```

## 🚀 Uso

### Script Principal Interativo

```bash
# Execute o script principal
python3 main.py
```

O script fornece um menu interativo com as seguintes opções:

```
╔════════════════════════════════════════════════════════╗
║                    MENU PRINCIPAL                      ║
╠════════════════════════════════════════════════════════╣
║  1. Mostrar informações do painel                      ║
║  2. Armar partição                                     ║
║  3. Desarmar partição                                  ║
║  4. Bypass de zona                                     ║
║  5. Ler status/memória (EEPROM)                        ║
║  6. Monitorar eventos em tempo real                    ║
║  7. Sair                                               ║
╚════════════════════════════════════════════════════════╝
```

### Exemplos de Uso Programático

```python
from paradox import SerialConnection, ParadoxPanel

# Configuração
config = {
    'pc_password': '0000',
    'model': 'MG5050'
}

# Conecta à porta serial
connection = SerialConnection('/dev/ttyUSB0', baudrate=9600)
connection.connect()

# Cria objeto do painel
panel = ParadoxPanel(connection, config)

# Handshake inicial
panel_info = panel.initiate_communication()
print(f"Painel: {panel_info['product_id']}")
print(f"Firmware: {panel_info['firmware_string']}")

# Autenticação
if panel.initialize_communication():
    print("Autenticado com sucesso!")
    
    # Arma partição 1 (modo regular)
    panel.arm_partition(partition=1, mode='arm')
    
    # Desarma partição 1
    panel.disarm_partition(partition=1)
    
    # Bypass de zona 5
    panel.bypass_zone(zone=5)
    
    # Lê status do painel
    data = panel.read_status(address=0x0000, records=1)
    
    # Monitora eventos
    for event in panel.monitor_events():
        print(f"Evento: {event}")

# Fecha conexão
connection.disconnect()
```

## 📡 Protocolo de Comunicação

### Especificações Técnicas

- **Baudrate**: 9600 bps
- **Formato**: 8 bits de dados, sem paridade, 1 stop bit (8N1)
- **Tamanho de mensagem**: 37 bytes (padrão)
- **Checksum**: Soma de todos os bytes módulo 256

### Fluxo de Comunicação

```
1. PC → Panel: InitiateCommunication (0x72 0x00)
   ├─ Comando de handshake inicial
   └─ 37 bytes

2. Panel → PC: InitiateCommunicationResponse (0x72 0xFF)
   ├─ Informações do painel
   ├─ Product ID, Firmware, Panel ID
   └─ 37 bytes

3. PC → Panel: InitializeCommunication (0x00)
   ├─ Autenticação com senha PC
   └─ 37 bytes

4. Panel → PC: InitializeCommunicationResponse
   ├─ 0x10 = Sucesso
   ├─ 0x70 = Falha (senha incorreta)
   └─ 37 bytes

5. PC ↔ Panel: Troca de comandos
   ├─ PerformAction (0x40): arm/disarm/bypass
   ├─ ReadEEPROM (0x50): leitura de memória
   └─ LiveEvent (0xE0-0xEF): eventos em tempo real
```

### Estrutura de Mensagem Padrão (37 bytes)

```
┌─────────┬──────────┬────────┬──────────┬──────────┬──────────┬──────────┐
│ Byte 0  │ Bytes    │ Byte N │ Byte N+1 │ Bytes    │ Byte 35  │ Byte 36  │
│ Command │ Header   │ Action │ Argument │ Padding  │ User ID  │ Checksum │
└─────────┴──────────┴────────┴──────────┴──────────┴──────────┴──────────┘
```

### Códigos de Comando Principais

| Comando | Descrição | Direção |
|---------|-----------|---------|
| `0x72` | InitiateCommunication | PC → Panel |
| `0x72 0xFF` | InitiateCommunicationResponse | Panel → PC |
| `0x00` | InitializeCommunication (MG/SP) | PC → Panel |
| `0x10` | InitializeCommunicationResponse (Success) | Panel → PC |
| `0x70` | InitializeCommunicationResponse (Fail) | Panel → PC |
| `0x40` | PerformAction | PC → Panel |
| `0x40-0x4F` | PerformActionResponse | Panel → PC |
| `0x50` | ReadEEPROM | PC → Panel |
| `0x50-0x5F` | ReadEEPROMResponse | Panel → PC |
| `0xE0-0xEF` | LiveEvent | Panel → PC |

### Ações de Partição

| Ação | Código | Descrição |
|------|--------|-----------|
| Arm (Away) | `0x04` | Armamento regular |
| Disarm | `0x05` | Desarmamento |
| Arm Stay | `0x01` | Armamento stay (permanência) |
| Arm Sleep | `0x02` | Armamento sleep |
| Arm Instant | `0x07` | Armamento instantâneo |
| Arm Stay Instant | `0x06` | Armamento stay instantâneo |

### Ações de Zona

| Ação | Código | Descrição |
|------|--------|-----------|
| Bypass | `0x10` | Bypass de zona (toggle) |

### Cálculo de Checksum

```python
def calculate_checksum(data):
    """Soma de todos os bytes módulo 256"""
    return sum(data) % 256

# Exemplo
message = bytearray([0x72, 0x00, ...])  # 36 bytes
checksum = calculate_checksum(message)
message.append(checksum)  # 37 bytes total
```

## 📁 Estrutura do Projeto

```
paradox-serial-interface/
├── README.md                    # Esta documentação
├── requirements.txt             # Dependências Python
├── config.yaml                  # Arquivo de configuração
├── main.py                      # Script principal interativo
├── .gitignore                   # Arquivos ignorados pelo git
└── paradox/                     # Pacote principal
    ├── __init__.py              # Inicialização do pacote
    ├── protocol.py              # Protocolo e parsers (construct)
    ├── connection.py            # Comunicação serial
    ├── panel.py                 # Lógica do painel MG/SP
    └── commands.py              # Comandos e helpers
```

## 🔍 Debug e Troubleshooting

### Habilitar Logging Detalhado

No `config.yaml`:
```yaml
logging:
  level: "DEBUG"
  dump_packets: true
```

### Captura de Tráfego Serial

**Linux - socat:**
```bash
# Instale socat
sudo apt-get install socat

# Crie par de portas virtuais
socat -d -d pty,raw,echo=0 pty,raw,echo=0

# Use uma porta no seu programa e monitore a outra
cat /dev/pts/X | hexdump -C
```

**Linux - interceptty:**
```bash
# Instale interceptty
sudo apt-get install interceptty

# Intercepte tráfego
interceptty -s 'ispeed 9600 ospeed 9600' /dev/ttyUSB0 /dev/pts/X
```

### Problemas Comuns

#### ❌ "Permission denied" ao abrir porta serial

**Linux:**
```bash
# Adicione usuário ao grupo dialout
sudo usermod -a -G dialout $USER
# Faça logout/login

# Ou execute com sudo
sudo python3 main.py
```

#### ❌ Sem resposta do painel

1. Verifique conexões físicas
2. Confirme level shifter está funcionando
3. Teste com voltímetro: ~5V nos pinos da central
4. Verifique porta serial correta no config.yaml
5. Tente outro conversor USB-TTL

#### ❌ "Falha na autenticação"

1. Verifique senha PC no Babyware
2. Confirme senha no config.yaml (4 dígitos hex)
3. Verifique se firmware é < 7.50

#### ❌ Mensagens truncadas/corrompidas

1. Reduza comprimento do cabo serial
2. Adicione capacitor (100nF) próximo ao level shifter
3. Verifique alimentação estável
4. Tente baudrate mais baixo (4800)

## 🎓 Próximos Passos - STM32

Este projeto serve como base para implementação em STM32F411:

### Arquitetura Proposta

```
┌────────────────────────────────────────────────────┐
│ STM32F411 + Módulo Ethernet (W5500/ENC28J60)      │
├────────────────────────────────────────────────────┤
│                                                    │
│  ┌─────────────┐      ┌──────────────┐           │
│  │  UART       │←────→│ Level Shifter│←──→ Paradox│
│  │  (Serial)   │      │  (5V ↔ 3.3V) │      Panel │
│  └─────────────┘      └──────────────┘           │
│        ↕                                          │
│  ┌─────────────┐                                 │
│  │  Ethernet   │←────→ Rede Local / Internet     │
│  │  (W5500)    │                                 │
│  └─────────────┘                                 │
│                                                   │
│  ┌─────────────────────────────────────────┐    │
│  │ Firmware C (baseado neste Python)       │    │
│  │ - Parser de protocolo Paradox           │    │
│  │ - Servidor HTTP/REST API                │    │
│  │ - Cliente MQTT (opcional)               │    │
│  │ - WebSocket para eventos em tempo real  │    │
│  └─────────────────────────────────────────┘    │
└────────────────────────────────────────────────────┘
```

### Benefícios

- ✅ Alternativa de baixo custo ao IP150
- ✅ Controle total sobre firmware
- ✅ Integração personalizada (MQTT, HTTP, etc)
- ✅ Monitoramento em tempo real via rede

## 📚 Referências

### Projeto Original

- **ParadoxAlarmInterface (PAI)**: https://github.com/ParadoxAlarmInterface/pai
  - Excelente projeto que serviu de base para engenharia reversa
  - Suporta integração com Home Assistant, MQTT, etc
  - Implementação completa em Python

### Documentação Útil

- **Construct Library**: https://construct.readthedocs.io/
  - Biblioteca Python para parsing de estruturas binárias
  - Usada para definir formato de mensagens Paradox

- **PySerial**: https://pyserial.readthedocs.io/
  - Biblioteca Python para comunicação serial
  - Multiplataforma (Windows, Linux, macOS)

### Hardware

- **FTDI FT232RL**: Conversor USB-TTL confiável e popular
- **CH340**: Alternativa econômica ao FTDI
- **Level Shifter Bidirecional**: BSS138, 74LVC245, ou similar

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Faça fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -am 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## ⚖️ Licença

Este projeto é fornecido "como está", sem garantias. Use por sua conta e risco.

**Aviso Legal**: 
- Este projeto é baseado em engenharia reversa e não é oficialmente suportado pela Paradox
- Use apenas em equipamentos que você possui
- Não nos responsabilizamos por danos ao equipamento ou problemas de segurança

## ✉️ Contato

Para questões, sugestões ou problemas, abra uma issue no GitHub.

---

**⚠️ IMPORTANTE**: Este é um projeto educacional. Para uso em produção, considere soluções oficiais ou o projeto PAI completo.

**🔒 SEGURANÇA**: Nunca exponha sua central de alarme diretamente à internet sem medidas adequadas de segurança (VPN, autenticação forte, etc).