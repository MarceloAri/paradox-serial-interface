"""
Módulo de protocolo Paradox - Parsers e estruturas de mensagens

Implementa o protocolo de comunicação serial com centrais Paradox MG/SP/Digiplex
baseado na engenharia reversa do projeto ParadoxAlarmInterface/pai.
"""

from construct import (
    Struct, Bytes, Int8ub, Int16ub, Enum, Const, Padding, 
    this, Computed, GreedyBytes, Flag, Array
)
import logging

logger = logging.getLogger(__name__)

# ===============================================================================
# CHECKSUMS
# ===============================================================================

def calculate_checksum(data):
    """
    Calcula checksum como soma de todos os bytes módulo 256
    
    Args:
        data: bytes - dados para calcular checksum
    
    Returns:
        int - checksum (0-255)
    """
    if isinstance(data, (list, tuple)):
        return sum(data) % 256
    return sum(data) % 256


# ===============================================================================
# ENUMERAÇÕES
# ===============================================================================

ProductIdEnum = Enum(
    Int8ub,
    DIGIPLEX_DGP2_48_NE=0,
    DIGIPLEX_DGP2_72_NE=1,
    DIGIPLEX_DGP2_96_NE=2,
    DIGIPLEX_DGP2_112_NE=3,
    DIGIPLEX_DGP2_816_NE=4,
    DIGIPLEX_DGP2_248_NE=5,
    MAGELLAN_MG5000=2,
    MAGELLAN_MG5050=4,
    SPECTRA_SP4000=5,
    SPECTRA_SP5500=21,
    SPECTRA_SP6000=22,
    SPECTRA_SP7000=23,
    SPECTRA_SP65=24,
)

CommunicationSourceIDEnum = Enum(
    Int8ub,
    BOOT_LOADER=0,
    PANEL_APP=1,
    NEware=2,
    IP100=4,
    Winload=5,
    WinloadApp=6,
    default=1
)

# ===============================================================================
# CONSTANTES DE AÇÕES
# ===============================================================================

# Ações de Partição
PARTITION_ACTIONS = {
    'arm_stay': 0x01,
    'arm_sleep': 0x02,
    'arm': 0x04,           # arm_away / regular arm
    'disarm': 0x05,
    'arm_stay_instant': 0x06,
    'arm_instant': 0x07,
}

# Ações de Zona
ZONE_ACTIONS = {
    'bypass': 0x10,
    'clear_bypass': 0x10,  # Mesmo código, toggle
}

# Ações PGM
PGM_ACTIONS = {
    'on': 0x32,
    'off': 0x33,
    'on_override': 0x34,
    'off_override': 0x35,
}

# ===============================================================================
# PARSERS - COMUNICAÇÃO INICIAL
# ===============================================================================

# Mensagem: Initiate Communication (0x72 0x00)
# PC -> Panel: Inicia handshake
InitiateCommunication = Struct(
    "fields" / Struct(
        "po" / Struct(
            "command" / Const(0x72, Int8ub),
        ),
        "reserved_0" / Padding(34),
        "user_id" / Int8ub,
    ),
    "checksum" / Int8ub,
)

# Mensagem: Initiate Communication Response (0x72 0xFF)
# Panel -> PC: Responde com informações do painel
InitiateCommunicationResponse = Struct(
    "fields" / Struct(
        "po" / Struct(
            "command" / Const(0x72, Int8ub),
            "result" / Const(0xFF, Int8ub),
        ),
        "reserved_0" / Bytes(4),
        "product_id" / ProductIdEnum,
        "firmware_version" / Struct(
            "version" / Int8ub,
            "revision" / Int8ub,
            "minor" / Int8ub,
        ),
        "panel_id" / Int16ub,
        "pc_password" / Bytes(2),
        "modem_speed" / Int8ub,
        "reserved_1" / Bytes(14),
        "source_id" / Int8ub,
        "user_id" / Int8ub,
        "receiver_line" / Bytes(4),
        "reserved_2" / Bytes(1),
    ),
    "checksum" / Int8ub,
)

# ===============================================================================
# PARSERS - AUTENTICAÇÃO MG/SP
# ===============================================================================

# Mensagem: Initialize Communication MG/SP (0x00)
# PC -> Panel: Autenticação com senha PC
InitializeCommunication_MGSP = Struct(
    "fields" / Struct(
        "po" / Struct(
            "command" / Const(0x00, Int8ub),
        ),
        "product_id" / ProductIdEnum,
        "firmware_version" / Struct(
            "version" / Int8ub,
            "revision" / Int8ub,
            "minor" / Int8ub,
        ),
        "panel_id" / Int16ub,
        "pc_password" / Bytes(2),
        "reserved_0" / Bytes(3),
        "source_id" / CommunicationSourceIDEnum,
        "user_id" / Const(0x00, Int8ub),
        "reserved_1" / Bytes(19),
    ),
    "checksum" / Int8ub,
)

# Mensagem: Initialize Communication Response MG/SP (0x10 = sucesso, 0x70 = falha)
InitializeCommunicationResponse_MGSP = Struct(
    "fields" / Struct(
        "po" / Struct(
            "command" / Int8ub,  # 0x10 sucesso, 0x70 falha senha
        ),
        "reserved_0" / Bytes(33),
        "user_id" / Int8ub,
    ),
    "checksum" / Int8ub,
)

# ===============================================================================
# PARSERS - COMANDOS E RESPOSTAS
# ===============================================================================

# Mensagem: Perform Action (0x40)
# PC -> Panel: Executa ação (arm/disarm/bypass/pgm)
PerformAction = Struct(
    "fields" / Struct(
        "po" / Struct(
            "command" / Const(0x40, Int8ub),
        ),
        "reserved_0" / Bytes(3),
        "action" / Int8ub,        # Código da ação (ex: 0x04=arm, 0x05=disarm)
        "argument" / Int8ub,      # Argumento (número da partição/zona)
        "reserved_1" / Bytes(27),
        "source_id" / CommunicationSourceIDEnum,
        "user_id" / Int8ub,
    ),
    "checksum" / Int8ub,
)

# Mensagem: Perform Action Response (0x4X)
# Panel -> PC: Resultado da ação
PerformActionResponse = Struct(
    "fields" / Struct(
        "po" / Struct(
            "command" / Int8ub,  # 0x40-0x4F dependendo do resultado
        ),
        "reserved_0" / Bytes(33),
        "user_id" / Int8ub,
    ),
    "checksum" / Int8ub,
)

# ===============================================================================
# PARSERS - LEITURA DE MEMÓRIA (EEPROM)
# ===============================================================================

# Mensagem: Read EEPROM (0x50)
# PC -> Panel: Lê memória do painel (status/configuração/eventos)
ReadEEPROM = Struct(
    "fields" / Struct(
        "po" / Struct(
            "command" / Const(0x50, Int8ub),
        ),
        "reserved_0" / Bytes(1),
        "address" / Int16ub,      # Endereço EEPROM para ler
        "records" / Int8ub,       # Número de registros
        "reserved_1" / Bytes(28),
        "source_id" / CommunicationSourceIDEnum,
        "user_id" / Int8ub,
    ),
    "checksum" / Int8ub,
)

# Mensagem: Read EEPROM Response (0x5X)
# Panel -> PC: Dados da EEPROM
ReadEEPROMResponse = Struct(
    "fields" / Struct(
        "po" / Struct(
            "command" / Int8ub,  # 0x50-0x5F
        ),
        "reserved_0" / Bytes(1),
        "address" / Int16ub,
        "records" / Int8ub,
        "data" / Bytes(32 - 5),  # Dados lidos (restante do payload)
    ),
    "checksum" / Int8ub,
)

# ===============================================================================
# PARSERS - EVENTOS EM TEMPO REAL
# ===============================================================================

# Mensagem: Live Event (0xEX)
# Panel -> PC: Eventos em tempo real (zonas, partições, alarmes)
LiveEvent = Struct(
    "fields" / Struct(
        "po" / Struct(
            "command" / Int8ub,  # 0xE0-0xEF
        ),
        "reserved_0" / Bytes(1),
        "event_group" / Int8ub,   # Grupo do evento
        "event_1" / Int8ub,       # Evento 1
        "event_2" / Int8ub,       # Evento 2
        "partition" / Int8ub,     # Partição
        "module_serial" / Bytes(4),
        "label_type" / Int8ub,
        "label" / Bytes(16),
        "reserved_1" / Bytes(6),
        "user_id" / Int8ub,
    ),
    "checksum" / Int8ub,
)

# ===============================================================================
# PARSER GENÉRICO
# ===============================================================================

def get_parser_by_command(command_byte):
    """
    Retorna o parser apropriado baseado no byte de comando
    
    Args:
        command_byte: int - primeiro byte da mensagem
    
    Returns:
        Parser construct ou None
    """
    parsers = {
        0x72: InitiateCommunicationResponse,  # Pode ser request ou response
        0x00: InitializeCommunication_MGSP,
        0x10: InitializeCommunicationResponse_MGSP,
        0x70: InitializeCommunicationResponse_MGSP,  # Falha de senha
        0x40: PerformAction,
        0x50: ReadEEPROM,
    }
    
    # Comandos com range
    if 0x40 <= command_byte <= 0x4F:
        return PerformActionResponse
    if 0x50 <= command_byte <= 0x5F:
        return ReadEEPROMResponse
    if 0xE0 <= command_byte <= 0xEF:
        return LiveEvent
    
    return parsers.get(command_byte)


def parse_message(data):
    """
    Tenta fazer parse de uma mensagem baseado no comando
    
    Args:
        data: bytes - mensagem completa (37 bytes normalmente)
    
    Returns:
        dict - mensagem parseada ou None se falhar
    """
    if len(data) < 2:
        return None
    
    command_byte = data[0]
    parser = get_parser_by_command(command_byte)
    
    if parser is None:
        logger.warning(f"Parser não encontrado para comando 0x{command_byte:02X}")
        return None
    
    try:
        parsed = parser.parse(data)
        return parsed
    except Exception as e:
        logger.error(f"Erro ao fazer parse da mensagem: {e}")
        return None


# ===============================================================================
# BUILDERS - CONSTRUÇÃO DE MENSAGENS
# ===============================================================================

def build_initiate_communication(user_id=0x00):
    """Constrói mensagem InitiateCommunication"""
    data = bytearray(37)
    data[0] = 0x72  # Command
    data[35] = user_id
    data[36] = calculate_checksum(data[0:36])
    return bytes(data)


def build_initialize_communication_mgsp(product_id, firmware_version, panel_id, pc_password_bytes, source_id=0x01, user_id=0x00):
    """
    Constrói mensagem InitializeCommunication_MGSP
    
    Args:
        product_id: int - ID do produto
        firmware_version: tuple - (version, revision, minor)
        panel_id: int - ID do painel
        pc_password_bytes: bytes - senha PC (2 bytes)
        source_id: int - ID da fonte (default Winload=5)
        user_id: int - ID do usuário
    """
    data = bytearray(37)
    data[0] = 0x00  # Command
    data[1] = product_id
    data[2] = firmware_version[0]
    data[3] = firmware_version[1]
    data[4] = firmware_version[2]
    data[5] = (panel_id >> 8) & 0xFF  # Panel ID high byte
    data[6] = panel_id & 0xFF         # Panel ID low byte
    data[7:9] = pc_password_bytes
    # reserved 9-11
    data[12] = source_id
    data[13] = user_id
    # reserved 14-34
    data[35] = user_id
    data[36] = calculate_checksum(data[0:36])
    return bytes(data)


def build_perform_action(action, argument, source_id=0x01, user_id=0x00):
    """
    Constrói mensagem PerformAction
    
    Args:
        action: int - código da ação
        argument: int - argumento (partição/zona)
        source_id: int - ID da fonte
        user_id: int - ID do usuário
    """
    data = bytearray(37)
    data[0] = 0x40  # Command
    # reserved 1-3
    data[4] = action
    data[5] = argument
    # reserved 6-32
    data[33] = source_id
    data[34] = user_id
    data[35] = user_id
    data[36] = calculate_checksum(data[0:36])
    return bytes(data)


def build_read_eeprom(address, records=1, source_id=0x01, user_id=0x00):
    """
    Constrói mensagem ReadEEPROM
    
    Args:
        address: int - endereço EEPROM
        records: int - número de registros
        source_id: int - ID da fonte
        user_id: int - ID do usuário
    """
    data = bytearray(37)
    data[0] = 0x50  # Command
    # reserved 1
    data[2] = (address >> 8) & 0xFF  # Address high byte
    data[3] = address & 0xFF         # Address low byte
    data[4] = records
    # reserved 5-32
    data[33] = source_id
    data[34] = user_id
    data[35] = user_id
    data[36] = calculate_checksum(data[0:36])
    return bytes(data)
