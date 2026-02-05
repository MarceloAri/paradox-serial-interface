#!/usr/bin/env python3
"""
Script principal de teste - Paradox Serial Interface

Menu interativo para testar comunicação com centrais Paradox MG/SP.
"""

import sys
import yaml
import logging
import time
from pathlib import Path

# Importa módulos do projeto
from paradox import SerialConnection, ParadoxPanel, protocol, commands


def setup_logging(config):
    """
    Configura sistema de logging
    
    Args:
        config: dict - configuração de logging
    """
    level_str = config.get('logging', {}).get('level', 'INFO')
    level = getattr(logging, level_str.upper(), logging.INFO)
    
    # Formato com cores (funciona em terminais Unix)
    class ColoredFormatter(logging.Formatter):
        """Formatter que adiciona cores aos logs"""
        
        COLORS = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
        }
        RESET = '\033[0m'
        
        def format(self, record):
            color = self.COLORS.get(record.levelname, self.RESET)
            record.levelname = f"{color}{record.levelname}{self.RESET}"
            return super().format(record)
    
    # Configura handler
    handler = logging.StreamHandler()
    
    # Tenta usar cores se possível
    try:
        formatter = ColoredFormatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            datefmt='%H:%M:%S'
        )
    except:
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            datefmt='%H:%M:%S'
        )
    
    handler.setFormatter(formatter)
    
    # Configura root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)


def load_config(config_path='config.yaml'):
    """
    Carrega arquivo de configuração
    
    Args:
        config_path: str - caminho do arquivo
    
    Returns:
        dict - configuração carregada
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        print(f"✓ Configuração carregada de {config_path}")
        return config
    except FileNotFoundError:
        print(f"✗ Arquivo de configuração não encontrado: {config_path}")
        print("  Usando configuração padrão")
        return {
            'serial': {
                'port': '/dev/ttyUSB0',
                'baudrate': 9600,
                'timeout': 5
            },
            'panel': {
                'pc_password': '0000',
                'model': 'MG5050'
            },
            'logging': {
                'level': 'INFO',
                'dump_packets': True
            }
        }
    except Exception as e:
        print(f"✗ Erro ao carregar configuração: {e}")
        sys.exit(1)


def print_banner():
    """Exibe banner do aplicativo"""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║      Paradox Serial Interface - Interface de Teste       ║
║                                                           ║
║  Comunicação com Centrais Paradox MG/SP via Serial TTL   ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_panel_info(panel):
    """
    Exibe informações do painel
    
    Args:
        panel: ParadoxPanel - painel conectado
    """
    if not panel.panel_info:
        print("✗ Informações do painel não disponíveis")
        return
    
    info = panel.panel_info
    
    print("\n" + "="*60)
    print("INFORMAÇÕES DO PAINEL")
    print("="*60)
    print(f"Produto:          {info.get('product_id', 'Desconhecido')}")
    print(f"Firmware:         {info.get('firmware_string', 'N/A')}")
    print(f"Panel ID:         {info.get('panel_id', 'N/A')}")
    print(f"Source ID:        {info.get('source_id', 'N/A')}")
    print("="*60 + "\n")


def show_main_menu():
    """Exibe menu principal"""
    menu = """
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
"""
    print(menu)


def show_arm_menu():
    """Exibe submenu de armamento"""
    menu = """
Modos de Armamento:
  1. Arm (Regular/Away)
  2. Arm Stay
  3. Arm Sleep
  4. Arm Instant
  5. Arm Stay Instant
  0. Voltar
"""
    print(menu)


def get_user_input(prompt, input_type=str, default=None):
    """
    Obtém entrada do usuário com validação
    
    Args:
        prompt: str - texto do prompt
        input_type: type - tipo esperado (int, str, etc)
        default: any - valor padrão
    
    Returns:
        Valor convertido ou default
    """
    try:
        user_input = input(prompt).strip()
        if not user_input and default is not None:
            return default
        return input_type(user_input)
    except (ValueError, KeyboardInterrupt):
        return default


def handle_arm_partition(panel):
    """
    Manipula armamento de partição
    
    Args:
        panel: ParadoxPanel - painel conectado
    """
    show_arm_menu()
    mode_choice = get_user_input("Escolha o modo de armamento: ", int, 0)
    
    if mode_choice == 0:
        return
    
    mode_map = {
        1: 'arm',
        2: 'arm_stay',
        3: 'arm_sleep',
        4: 'arm_instant',
        5: 'arm_stay_instant',
    }
    
    mode = mode_map.get(mode_choice)
    if mode is None:
        print("✗ Opção inválida")
        return
    
    partition = get_user_input("Número da partição (1-8): ", int, 1)
    
    if not (1 <= partition <= 8):
        print("✗ Partição inválida (deve ser 1-8)")
        return
    
    print(f"\nArmando partição {partition} (modo: {mode})...")
    success = panel.arm_partition(partition, mode)
    
    if success:
        print("✓ Comando de armamento enviado com sucesso")
    else:
        print("✗ Falha ao enviar comando de armamento")


def handle_disarm_partition(panel):
    """
    Manipula desarmamento de partição
    
    Args:
        panel: ParadoxPanel - painel conectado
    """
    partition = get_user_input("Número da partição (1-8): ", int, 1)
    
    if not (1 <= partition <= 8):
        print("✗ Partição inválida (deve ser 1-8)")
        return
    
    print(f"\nDesarmando partição {partition}...")
    success = panel.disarm_partition(partition)
    
    if success:
        print("✓ Comando de desarmamento enviado com sucesso")
    else:
        print("✗ Falha ao enviar comando de desarmamento")


def handle_bypass_zone(panel):
    """
    Manipula bypass de zona
    
    Args:
        panel: ParadoxPanel - painel conectado
    """
    zone = get_user_input("Número da zona (1-192): ", int, 1)
    
    if not (1 <= zone <= 192):
        print("✗ Zona inválida (deve ser 1-192)")
        return
    
    print(f"\nFazendo bypass da zona {zone}...")
    success = panel.bypass_zone(zone)
    
    if success:
        print("✓ Comando de bypass enviado com sucesso")
    else:
        print("✗ Falha ao enviar comando de bypass")


def handle_read_status(panel):
    """
    Manipula leitura de status
    
    Args:
        panel: ParadoxPanel - painel conectado
    """
    print("\nEndereços comuns:")
    print("  0x0000 - Status de partições")
    print("  0x0010 - Status de zonas")
    print("  0x0100 - Configuração do painel")
    
    address_str = get_user_input("Endereço EEPROM (hex, ex: 0000): ", str, "0000")
    
    try:
        address = int(address_str, 16)
    except ValueError:
        print("✗ Endereço inválido")
        return
    
    records = get_user_input("Número de registros (1-32): ", int, 1)
    
    if not (1 <= records <= 32):
        print("✗ Número de registros inválido")
        return
    
    print(f"\nLendo EEPROM endereço 0x{address:04X} ({records} registro(s))...")
    data = panel.read_status(address, records)
    
    if data:
        print("✓ Dados lidos com sucesso:")
        print(commands.format_hex_dump(data))
    else:
        print("✗ Falha ao ler dados")


def handle_monitor_events(panel):
    """
    Manipula monitoramento de eventos
    
    Args:
        panel: ParadoxPanel - painel conectado
    """
    print("\nMonitorando eventos em tempo real...")
    print("Pressione Ctrl+C para parar\n")
    
    try:
        for event in panel.monitor_events():
            print(f"\n{'='*60}")
            print(f"EVENTO RECEBIDO")
            print(f"{'='*60}")
            print(f"Comando:      0x{event['command']:02X}")
            print(f"Grupo:        {event['event_group']}")
            print(f"Evento 1:     {event['event_1']}")
            print(f"Evento 2:     {event['event_2']}")
            print(f"Partição:     {event['partition']}")
            print(f"Label Type:   {event['label_type']}")
            print(f"Label:        {event['label']}")
            print(f"{'='*60}\n")
    except KeyboardInterrupt:
        print("\n✓ Monitoramento interrompido")


def main():
    """Função principal"""
    print_banner()
    
    # Carrega configuração
    config = load_config()
    
    # Configura logging
    setup_logging(config)
    logger = logging.getLogger(__name__)
    
    # Extrai configurações
    serial_config = config.get('serial', {})
    panel_config = config.get('panel', {})
    
    print(f"\nConfigurações:")
    print(f"  Porta Serial:  {serial_config.get('port', 'N/A')}")
    print(f"  Baudrate:      {serial_config.get('baudrate', 'N/A')}")
    print(f"  Modelo Painel: {panel_config.get('model', 'N/A')}")
    print(f"  Senha PC:      {'*' * len(panel_config.get('pc_password', ''))}")
    print()
    
    # Cria conexão serial
    try:
        connection = SerialConnection(
            port=serial_config.get('port', '/dev/ttyUSB0'),
            baudrate=serial_config.get('baudrate', 9600),
            timeout=serial_config.get('timeout', 5)
        )
        
        print("Conectando à porta serial...")
        connection.connect()
        print("✓ Conexão serial estabelecida\n")
        
    except Exception as e:
        print(f"✗ Erro ao conectar porta serial: {e}")
        print("\nDica: Verifique se a porta está correta e você tem permissões adequadas")
        print("      Linux: sudo usermod -a -G dialout $USER (requer logout)")
        print("      Linux: ou execute com sudo")
        sys.exit(1)
    
    # Cria objeto do painel
    panel = ParadoxPanel(connection, panel_config)
    
    # Executa handshake
    try:
        print("Executando handshake com painel (InitiateCommunication)...")
        panel_info = panel.initiate_communication()
        
        if not panel_info:
            print("✗ Falha no handshake - Verifique conexão física")
            connection.disconnect()
            sys.exit(1)
        
        print("✓ Handshake bem-sucedido")
        print_panel_info(panel)
        
        # Executa autenticação
        print("Autenticando com painel (InitializeCommunication)...")
        authenticated = panel.initialize_communication()
        
        if not authenticated:
            print("✗ Falha na autenticação - Verifique senha PC")
            connection.disconnect()
            sys.exit(1)
        
        print("✓ Autenticação bem-sucedida\n")
        
    except Exception as e:
        logger.error(f"Erro durante inicialização: {e}")
        connection.disconnect()
        sys.exit(1)
    
    # Menu interativo
    try:
        while True:
            show_main_menu()
            choice = get_user_input("Escolha uma opção: ", int, 0)
            
            if choice == 1:
                print_panel_info(panel)
            
            elif choice == 2:
                handle_arm_partition(panel)
            
            elif choice == 3:
                handle_disarm_partition(panel)
            
            elif choice == 4:
                handle_bypass_zone(panel)
            
            elif choice == 5:
                handle_read_status(panel)
            
            elif choice == 6:
                handle_monitor_events(panel)
            
            elif choice == 7:
                print("\nEncerrando...")
                break
            
            else:
                print("✗ Opção inválida")
            
            # Pausa antes de mostrar menu novamente
            if choice != 7:
                input("\nPressione Enter para continuar...")
    
    except KeyboardInterrupt:
        print("\n\nInterrompido pelo usuário")
    
    finally:
        # Fecha conexão
        print("\nFechando conexão...")
        connection.disconnect()
        print("✓ Conexão fechada\n")


if __name__ == '__main__':
    main()
