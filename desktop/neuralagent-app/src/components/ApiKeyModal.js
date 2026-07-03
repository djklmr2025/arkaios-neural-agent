import React, { useState } from 'react';
import styled from 'styled-components';
import { ClipLoader } from 'react-spinners';

const Overlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(10, 10, 20, 0.85);
  backdrop-filter: blur(12px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
`;

const ModalContainer = styled.div`
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 40px;
  width: 90%;
  max-width: 450px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  gap: 20px;
  color: #fff;
  font-family: 'Inter', sans-serif;
`;

const Title = styled.h2`
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  text-align: center;
  background: linear-gradient(135deg, #00D9C0, #7C3AED);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
`;

const Description = styled.p`
  margin: 0;
  font-size: 14px;
  color: #a1a1aa;
  text-align: center;
  line-height: 1.5;

  a {
    color: #00D9C0;
    text-decoration: none;
    &:hover {
      text-decoration: underline;
    }
  }
`;

const InputGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
`;

const Input = styled.input`
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 12px 16px;
  color: #fff;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;

  &:focus {
    border-color: #00D9C0;
  }
`;

const Select = styled.select`
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 12px 16px;
  color: #fff;
  font-size: 14px;
  outline: none;

  option {
    background: #111827;
  }
`;

const Button = styled.button`
  background: linear-gradient(135deg, #7C3AED, #00D9C0);
  border: none;
  border-radius: 8px;
  padding: 14px;
  color: #fff;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.1s;
  display: flex;
  justify-content: center;
  align-items: center;

  &:hover:not(:disabled) {
    opacity: 0.9;
  }
  
  &:active:not(:disabled) {
    transform: scale(0.98);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const SecondaryButton = styled(Button)`
  background: rgba(0, 217, 192, 0.18);
  border: 1px solid rgba(0, 217, 192, 0.35);
`;

const ErrorMsg = styled.div`
  color: #ef4444;
  font-size: 12px;
  text-align: center;
`;

const ApiKeyModal = ({ onSuccess }) => {
  const [provider, setProvider] = useState('puter');
  const [credential, setCredential] = useState('');
  const [modelId, setModelId] = useState('gpt-5-nano');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [puterStatus, setPuterStatus] = useState('');

  const handleProviderChange = (nextProvider) => {
    setProvider(nextProvider);
    setModelId(nextProvider === 'puter' ? 'gpt-5-nano' : 'gemini-2.5-flash');
    setCredential('');
    setError('');
    setPuterStatus('');
  };

  const handlePuterLogin = async () => {
    try {
      if (!window.puter?.auth?.signIn) {
        setPuterStatus('Puter.js no esta disponible en este entorno.');
        return;
      }
      await window.puter.auth.signIn();
      const user = window.puter.auth.getUser ? await window.puter.auth.getUser() : null;
      
      let token = '';
      try {
        if (typeof window.puter.auth.getToken === 'function') {
          token = await window.puter.auth.getToken();
        } else if (window.puter.authToken) {
          token = window.puter.authToken;
        } else {
          // Fallback para extraer token del localStorage de puter
          token = window.localStorage.getItem('puter_auth_token') || '';
        }
      } catch (e) {
        console.error("Error extrayendo token:", e);
      }

      if (token) {
        setCredential(token);
        setPuterStatus(user?.username ? `Puter conectado como ${user.username}. Token auto-inyectado.` : 'Puter conectado. Token inyectado.');
      } else {
        setPuterStatus(user?.username ? `Puter conectado como ${user.username}. (No se pudo auto-inyectar token)` : 'Puter conectado.');
      }
    } catch (err) {
      setPuterStatus('No se completo el inicio de sesion con Puter.');
    }
  };

  const handleSubmit = async () => {
    if (!credential || credential.trim().length < 10) {
      setError(provider === 'puter' ? 'Por favor ingresa un Puter Auth Token valido.' : 'Por favor ingresa una API Key valida.');
      return;
    }
    
    setError('');
    setLoading(true);

    try {
      if (window.electronAPI?.saveAiProviderConfig || window.electronAPI?.saveApiKey) {
        const success = window.electronAPI.saveAiProviderConfig
          ? await window.electronAPI.saveAiProviderConfig({
              provider,
              credential: credential.trim(),
              modelId: modelId.trim(),
            })
          : await window.electronAPI.saveApiKey(credential.trim());

        if (success) {
          setTimeout(async () => {
            try {
              const res = await fetch('http://127.0.0.1:8000/apps/system/ping_llm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: 'Hola estas viv@?', agent: 'classifier' })
              });
              
              const data = await res.json();
              if (res.ok && data.status === 'success') {
                setSuccessMessage(data.message);
                setTimeout(() => {
                  setLoading(false);
                  onSuccess();
                }, 4000);
              } else {
                setError(provider === 'puter' ? 'Token Puter invalido o conexion rechazada.' : 'Llave invalida o conexion rechazada.');
                setLoading(false);
              }
            } catch (pingErr) {
              setError('El Cerebro no respondio a tiempo. Intenta de nuevo.');
              setLoading(false);
            }
          }, 4000);
        } else {
          setError('Ocurrio un error al guardar la configuracion.');
          setLoading(false);
        }
      } else {
        setError('API de Electron no disponible.');
        setLoading(false);
      }
    } catch (err) {
      setError('Error interno.');
      setLoading(false);
    }
  };

  return (
    <Overlay>
      <ModalContainer>
        {successMessage ? (
          <>
            <Title style={{ color: '#00D9C0', background: 'none', WebkitTextFillColor: '#00D9C0' }}>Jaula Abierta</Title>
            <Description style={{ color: '#fff', fontSize: '16px', fontStyle: 'italic', padding: '20px', background: 'rgba(0,217,192,0.1)', borderRadius: '12px', border: '1px solid rgba(0,217,192,0.3)' }}>
              "{successMessage}"
            </Description>
          </>
        ) : (
          <>
            <Title>Inyeccion de Memoria</Title>
            <Description>
              Para despertar a ARKAIOS, elige un proveedor de IA. Puter permite que cada usuario use su propia cuenta; o puedes usar tu API Key propia (BYOK).
            </Description>

            <InputGroup>
              <Select value={provider} onChange={(e) => handleProviderChange(e.target.value)}>
                <option value="puter">Puter AI</option>
                <option value="google">API Key Propia (BYOK)</option>
              </Select>
            </InputGroup>

            {provider === 'puter' && (
              <>
                <SecondaryButton onClick={handlePuterLogin} disabled={loading}>
                  Conectar login Puter
                </SecondaryButton>
                {puterStatus && <Description>{puterStatus}</Description>}
              </>
            )}

            <InputGroup>
              <Input
                type="text"
                placeholder={provider === 'puter' ? 'Modelo Puter, ej. gpt-5-nano' : 'Modelo, ej. gemini-2.5-flash'}
                value={modelId}
                onChange={(e) => setModelId(e.target.value)}
              />
            </InputGroup>
            
            <InputGroup>
              <Input 
                type="password" 
                placeholder={provider === 'puter' ? 'Pega tu PUTER_AUTH_TOKEN aqui...' : 'Pega tu API Key aqui...'}
                value={credential}
                onChange={(e) => setCredential(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                autoFocus
              />
            </InputGroup>

            <Description>
              {provider === 'puter'
                ? 'Para automatizacion desktop, el backend necesita un token de tu cuenta Puter. No lo subas al repo.'
                : <>Introduce tu API Key propia para usar tu proveedor (OpenAI, Anthropic, Google, etc).</>}
            </Description>

            {error && <ErrorMsg>{error}</ErrorMsg>}

            <Button onClick={handleSubmit} disabled={loading}>
              {loading ? <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}><ClipLoader size={16} color="#fff" /> <span>Despertando a la IA...</span></div> : 'Guardar proveedor'}
            </Button>
          </>
        )}
      </ModalContainer>
    </Overlay>
  );
};

export default ApiKeyModal;
