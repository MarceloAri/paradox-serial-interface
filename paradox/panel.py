"""
Módulo de lógica do painel Paradox MG/SP

Implementa a interface de alto nível para comunicação com painéis Paradox.
"""

import logging
import time
from . import protocol
from .connection import SerialConnection

logger = logging.getLogger(__name__)


class ParadoxPanel:
    """
    Classe principal para gerenciar comunicação com painéis Paradox MG/SP
    
    Attributes:
        connection: SerialConnection - conexão serial
        config: dict - configuração do painel
        panel_info: dict - informações do painel (após handshake)
    """
    
    def __init__(self, connection, config):
        """
        Inicializa painel Paradox
        
        Args:
            connection: SerialConnection - conexão serial estabelecida
            config: dict - configuração (pc_password, model, etc)
        """
        self.connection = connection
        self.config = config
        self.panel_info = {}
        self._authenticated = False
    
    def encode_password(self, password):
        """
        Converte senha string para bytes
        
        Senha PC é 4 dígitos hexadecimais (0-9, a-f).
        Armazenada como 2 bytes.
        
        Args:
            password: str - senha como string (ex: "0000", "1234", "abcd")
        
        Returns:
            bytes - senha codificada (2 bytes)
        """
        if len(password) != 4:
            raise ValueError("Senha PC deve ter 4 caracteres hexadecimais")
        
        try:
            # Converte string hex para 2 bytes
            byte1 = int(password[0:2], 16)
            byte2 = int(password[2:4], 16)
            return bytes([byte1, byte2])
        except ValueError:
            raise ValueError("Senha PC deve conter apenas caracteres hexadecimais (0-9, a-f)")
    
    def initiate_communication(self):
        """
        Executa handshake inicial (InitiateCommunication 0x72)
        
        Envia comando 0x72 e aguarda resposta com informações do painel.
        
        Returns:
            dict - informações do painel ou None se falhar
        """
        logger.info("Iniciando comunicação com painel (InitiateCommunication)")
        
        # Limpa buffer
        self.connection.flush_input()
        
        # Constrói e envia comando
        cmd = protocol.build_initiate_communication(user_id=0x00)
        self.connection.write(cmd)
        
        # Aguarda resposta
        response = self.wait_for_response(0x72, timeout=5)
        if response is None:
            logger.error("Nenhuma resposta recebida do painel")
            return None
        
        # Faz parse da resposta
        try:
            parsed = protocol.InitiateCommunicationResponse.parse(response)
            
            # Extrai informações do painel
            self.panel_info = {
                'product_id': parsed.fields.product_id,
                'firmware_version': (
                    parsed.fields.firmware_version.version,
                    parsed.fields.firmware_version.revision,
                    parsed.fields.firmware_version.minor
                ),
                'firmware_string': f"{parsed.fields.firmware_version.version}.{parsed.fields.firmware_version.revision}.{parsed.fields.firmware_version.minor}",
                'panel_id': parsed.fields.panel_id,
                'pc_password': parsed.fields.pc_password,
                'source_id': parsed.fields.source_id,
            }
            
            logger.info(f"Painel identificado: {self.panel_info['product_id']} "
                       f"Firmware: {self.panel_info['firmware_string']} "
                       f"Panel ID: {self.panel_info['panel_id']}")
            
            return self.panel_info
            
        except Exception as e:
            logger.error(f"Erro ao processar resposta do painel: {e}")
            return None
    
    def initialize_communication(self):
        """
        Executa autenticação MG/SP (InitializeCommunication 0x00)
        
        Envia senha PC e aguarda confirmação.
        
        Returns:
            bool - True se autenticado com sucesso
        """
        if not self.panel_info:
            logger.error("Deve executar initiate_communication() primeiro")
            return False
        
        logger.info("Autenticando com painel (InitializeCommunication MG/SP)")
        
        # Codifica senha PC
        pc_password_str = self.config.get('pc_password', '0000')
        pc_password_bytes = self.encode_password(pc_password_str)
        
        # Constrói comando de autenticação
        cmd = protocol.build_initialize_communication_mgsp(
            product_id=self.panel_info['product_id'],
            firmware_version=self.panel_info['firmware_version'],
            panel_id=self.panel_info['panel_id'],
            pc_password_bytes=pc_password_bytes,
            source_id=0x01,  # Panel App
            user_id=0x00
        )
        
        self.connection.write(cmd)
        
        # Aguarda resposta
        response = self.wait_for_response([0x10, 0x70], timeout=5)
        if response is None:
            logger.error("Nenhuma resposta de autenticação recebida")
            return False
        
        # Verifica resultado
        result_code = response[0]
        if result_code == 0x10:
            logger.info("Autenticação bem-sucedida!")
            self._authenticated = True
            return True
        elif result_code == 0x70:
            logger.error("Falha na autenticação - senha PC incorreta")
            return False
        else:
            logger.error(f"Resposta de autenticação inesperada: 0x{result_code:02X}")
            return False
    
    def parse_message(self, data, direction="RX"):
        """
        Identifica e faz parse de mensagem
        
        Args:
            data: bytes - mensagem completa
            direction: str - "RX" ou "TX" para logging
        
        Returns:
            dict - mensagem parseada ou None
        """
        if len(data) < 2:
            return None
        
        command = data[0]
        logger.debug(f"[{direction}] Processando comando 0x{command:02X}")
        
        parsed = protocol.parse_message(data)
        return parsed
    
    def wait_for_response(self, expected_command, timeout=5):
        """
        Aguarda resposta com comando específico
        
        Args:
            expected_command: int ou list - comando(s) esperado(s)
            timeout: float - tempo máximo de espera
        
        Returns:
            bytes - mensagem recebida ou None se timeout
        """
        if isinstance(expected_command, int):
            expected_command = [expected_command]
        
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            # Verifica se há dados disponíveis
            if self.connection.available() > 0:
                # Lê mensagem
                data = self.connection.read_variable_length()
                
                if len(data) > 0:
                    command = data[0]
                    if command in expected_command:
                        return data
                    else:
                        logger.warning(f"Comando inesperado recebido: 0x{command:02X}, "
                                     f"esperado: {[f'0x{c:02X}' for c in expected_command]}")
            
            # Pequena pausa para não sobrecarregar CPU
            time.sleep(0.01)
        
        logger.warning(f"Timeout aguardando resposta. Esperado: {[f'0x{c:02X}' for c in expected_command]}")
        return None
    
    def send_command(self, command_data, expected_response=None, timeout=5):
        """
        Envia comando genérico e aguarda resposta
        
        Args:
            command_data: bytes - comando a enviar
            expected_response: int ou list - comando(s) de resposta esperado(s)
            timeout: float - tempo de espera
        
        Returns:
            bytes - resposta recebida ou None
        """
        self.connection.write(command_data)
        
        if expected_response is not None:
            return self.wait_for_response(expected_response, timeout)
        
        return None
    
    def arm_partition(self, partition, mode='arm'):
        """
        Arma partição
        
        Args:
            partition: int - número da partição (1-8)
            mode: str - modo de armamento:
                'arm' ou 'arm_away': armamento regular
                'arm_stay': armamento stay
                'arm_sleep': armamento sleep
                'arm_instant': armamento instantâneo
                'arm_stay_instant': armamento stay instantâneo
        
        Returns:
            bool - True se comando enviado com sucesso
        """
        if not self._authenticated:
            logger.error("Não autenticado - execute initialize_communication() primeiro")
            return False
        
        # Mapeia modo para código de ação
        action_code = protocol.PARTITION_ACTIONS.get(mode)
        if action_code is None:
            logger.error(f"Modo de armamento inválido: {mode}")
            return False
        
        logger.info(f"Armando partição {partition} (modo: {mode})")
        
        # Constrói comando
        cmd = protocol.build_perform_action(
            action=action_code,
            argument=partition - 1,  # Partições são 0-indexed no protocolo
            source_id=0x01,
            user_id=0x00
        )
        
        # Envia e aguarda resposta
        response = self.send_command(cmd, expected_response=list(range(0x40, 0x50)), timeout=5)
        
        if response:
            result_code = response[0]
            if result_code == 0x40:
                logger.info(f"Partição {partition} armada com sucesso")
                return True
            else:
                logger.warning(f"Resposta inesperada ao armar: 0x{result_code:02X}")
                return False
        else:
            logger.error("Timeout ao aguardar confirmação de armamento")
            return False
    
    def disarm_partition(self, partition):
        """
        Desarma partição
        
        Args:
            partition: int - número da partição (1-8)
        
        Returns:
            bool - True se comando enviado com sucesso
        """
        if not self._authenticated:
            logger.error("Não autenticado - execute initialize_communication() primeiro")
            return False
        
        logger.info(f"Desarmando partição {partition}")
        
        # Constrói comando
        cmd = protocol.build_perform_action(
            action=protocol.PARTITION_ACTIONS['disarm'],
            argument=partition - 1,
            source_id=0x01,
            user_id=0x00
        )
        
        # Envia e aguarda resposta
        response = self.send_command(cmd, expected_response=list(range(0x40, 0x50)), timeout=5)
        
        if response:
            result_code = response[0]
            if result_code == 0x40:
                logger.info(f"Partição {partition} desarmada com sucesso")
                return True
            else:
                logger.warning(f"Resposta inesperada ao desarmar: 0x{result_code:02X}")
                return False
        else:
            logger.error("Timeout ao aguardar confirmação de desarmamento")
            return False
    
    def bypass_zone(self, zone):
        """
        Faz bypass de zona
        
        Args:
            zone: int - número da zona (1-192)
        
        Returns:
            bool - True se comando enviado com sucesso
        """
        if not self._authenticated:
            logger.error("Não autenticado - execute initialize_communication() primeiro")
            return False
        
        logger.info(f"Fazendo bypass da zona {zone}")
        
        # Constrói comando
        cmd = protocol.build_perform_action(
            action=protocol.ZONE_ACTIONS['bypass'],
            argument=zone - 1,
            source_id=0x01,
            user_id=0x00
        )
        
        # Envia e aguarda resposta
        response = self.send_command(cmd, expected_response=list(range(0x40, 0x50)), timeout=5)
        
        if response:
            result_code = response[0]
            if result_code == 0x40:
                logger.info(f"Zona {zone} em bypass")
                return True
            else:
                logger.warning(f"Resposta inesperada ao fazer bypass: 0x{result_code:02X}")
                return False
        else:
            logger.error("Timeout ao aguardar confirmação de bypass")
            return False
    
    def read_status(self, address=0x0000, records=1):
        """
        Lê status/memória do painel
        
        Args:
            address: int - endereço EEPROM
            records: int - número de registros
        
        Returns:
            bytes - dados lidos ou None se falhar
        """
        if not self._authenticated:
            logger.error("Não autenticado - execute initialize_communication() primeiro")
            return None
        
        logger.info(f"Lendo EEPROM endereço 0x{address:04X} ({records} registro(s))")
        
        # Constrói comando
        cmd = protocol.build_read_eeprom(
            address=address,
            records=records,
            source_id=0x01,
            user_id=0x00
        )
        
        # Envia e aguarda resposta
        response = self.send_command(cmd, expected_response=list(range(0x50, 0x60)), timeout=5)
        
        if response:
            try:
                parsed = protocol.ReadEEPROMResponse.parse(response)
                logger.info(f"Dados EEPROM lidos: {len(parsed.fields.data)} bytes")
                return parsed.fields.data
            except Exception as e:
                logger.error(f"Erro ao processar resposta EEPROM: {e}")
                return None
        else:
            logger.error("Timeout ao aguardar resposta EEPROM")
            return None
    
    def handle_live_event(self, event_data):
        """
        Processa evento em tempo real
        
        Args:
            event_data: bytes - dados do evento (0xEX)
        
        Returns:
            dict - evento parseado ou None
        """
        try:
            parsed = protocol.LiveEvent.parse(event_data)
            
            event_info = {
                'command': parsed.fields.po.command,
                'event_group': parsed.fields.event_group,
                'event_1': parsed.fields.event_1,
                'event_2': parsed.fields.event_2,
                'partition': parsed.fields.partition,
                'label_type': parsed.fields.label_type,
                'label': parsed.fields.label.decode('ascii', errors='ignore').strip('\x00'),
            }
            
            logger.info(f"Evento recebido: Grupo={event_info['event_group']} "
                       f"Partição={event_info['partition']} "
                       f"Label={event_info['label']}")
            
            return event_info
            
        except Exception as e:
            logger.error(f"Erro ao processar evento: {e}")
            return None
    
    def monitor_events(self, duration=None):
        """
        Monitora eventos em tempo real
        
        Args:
            duration: float - duração em segundos (None = indefinido)
        
        Yields:
            dict - eventos recebidos
        """
        logger.info(f"Monitorando eventos{' por ' + str(duration) + 's' if duration else ' (pressione Ctrl+C para parar)'}")
        
        start_time = time.time()
        
        try:
            while True:
                # Verifica se deve parar
                if duration and (time.time() - start_time) >= duration:
                    break
                
                # Verifica se há dados disponíveis
                if self.connection.available() > 0:
                    data = self.connection.read_variable_length()
                    
                    if len(data) > 0:
                        command = data[0]
                        
                        # Eventos são 0xE0-0xEF
                        if 0xE0 <= command <= 0xEF:
                            event = self.handle_live_event(data)
                            if event:
                                yield event
                        else:
                            # Outras mensagens
                            logger.debug(f"Mensagem não-evento recebida: 0x{command:02X}")
                
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            logger.info("Monitoramento interrompido pelo usuário")
