import React, { useEffect, useState } from 'react';
import mqtt from 'mqtt';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Html } from '@react-three/drei';

export default function App() {
  const [liveData, setLiveData] = useState({
    timestamp: '-',
    index: '0',
    final_status: '대기 중...',
    cam1_gap_mm: 0,
    cam3_gap_mm: 0,
    screw_present: true
  });
  
  const [alertLog, setAlertLog] = useState([]); 
  const [timeTick, setTimeTick] = useState(Date.now());

  useEffect(() => {
    const client = mqtt.connect('ws://broker.emqx.io:8083/mqtt');

    client.on('connect', () => {
      console.log('🌐 MQTT 연동 성공 ');
      client.subscribe('capstone/line1/state/lhj'); 
    });

    client.on('message', (topic, message) => {
      const data = JSON.parse(message.toString());
      setLiveData(data);
      setTimeTick(Date.now()); 
      
      if (data.final_status === "SYSTEM_OFF") {
        setAlertLog([]); 
      } else {
        setAlertLog(prev => [{ id: Date.now(), ...data }, ...prev].slice(0, 15));
      }
    });

    return () => client.end();
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100vw', height: '100vh', background: '#0f172a', color: '#fff', fontFamily: 'sans-serif' }}>
      
      {/* 📸 상단: 3채널 멀티 뷰포트 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '15px', padding: '15px', height: '35%', background: '#1e293b', borderBottom: '2px solid #334155' }}>
        {['cam1', 'cam2', 'cam3'].map((cam, i) => (
          <div key={cam} style={{ position: 'relative', borderRadius: '8px', overflow: 'hidden', border: '1px solid #475569', background: '#000' }}>
            <div style={{ position: 'absolute', top: 8, left: 8, background: 'rgba(0,0,0,0.7)', padding: '4px 10px', borderRadius: '4px', fontSize: '14px', fontWeight: 'bold', zIndex: 5 }}>
              VIEW {i + 1} ({cam.toUpperCase()})
            </div>
            <img 
              src={`http://127.0.0.1:8000/live_${cam}.jpg?t=${timeTick}`} 
              alt={`${cam} 화면`}
              style={{ width: '100%', height: '100%', objectFit: 'contain' }} 
              onError={(e) => { e.target.src = "https://via.placeholder.com/600x400/1e293b/475569?text=Connecting+Signal..."; }}
            />
          </div>
        ))}
      </div>

      {/* 📊 하단: 알람 로그 , 3D 디지털 트윈 */}
      <div style={{ display: 'flex', flex: 1, padding: '15px', gap: '15px', overflow: 'hidden' }}>
        
        {/* 왼쪽: 실시간 검사 로그 */}
        <div style={{ width: '35%', background: '#1e293b', borderRadius: '12px', padding: '20px', border: '1px solid #334155', display: 'flex', flexDirection: 'column' }}>
          <h2 style={{ color: '#fff', borderBottom: '1px solid #475569', paddingBottom: '12px', marginTop: 0 }}>
            📋 실시간 공정 로그
          </h2>
          
          <div style={{ fontSize: '20px', marginBottom: '20px', fontWeight: 'bold' }}>
            현재 상태: <span style={{ color: liveData.final_status.includes('ERROR') ? '#ef4444' : liveData.final_status.includes('NG') ? '#fbbf24' : '#4ade80' }}>
              {liveData.final_status}
            </span>
          </div>

          <div style={{ overflowY: 'auto', flex: 1, paddingRight: '5px' }}>
            {alertLog.map(log => {
              const isError = log.final_status.includes('ERROR');
              const isNG = log.final_status.includes('NG');
              const statusColor = isError ? '#ef4444' : (isNG ? '#fbbf24' : '#4ade80');
              const bgColor = isError ? 'rgba(239, 68, 68, 0.1)' : (isNG ? 'rgba(251, 191, 36, 0.1)' : 'rgba(74, 222, 128, 0.05)');
              
              return (
                <div key={log.id} style={{ background: bgColor, padding: '12px', borderRadius: '8px', marginBottom: '10px', borderLeft: `4px solid ${statusColor}` }}>
                  <div style={{ color: '#94a3b8', fontSize: '12px', marginBottom: '4px' }}>[{log.timestamp}]</div>
                  <div style={{ fontWeight: 'bold', color: statusColor }}>{log.final_status}</div>
                  <div style={{ fontSize: '13px', color: '#cbd5e1', marginTop: '4px' }}>
                    Cam1 단차: {log.cam1_gap_mm}mm | Cam3 단차: {log.cam3_gap_mm}mm
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 오른쪽: 3D 디지털 트윈 공간  */}
        <div style={{ flex: 1, background: '#1e293b', borderRadius: '12px', border: '1px solid #334155', position: 'relative' }}>
          
          <Canvas camera={{ position: [2, 1.5, 3], fov: 45 }}>
            <ambientLight intensity={0.7} />
            <directionalLight position={[5, 10, 5]} intensity={1.5} />
            <OrbitControls makeDefault target={[0, 0.2, 0]} enableZoom={true} />
            <DigitalTwin gap={Math.max(liveData.cam1_gap_mm, liveData.cam3_gap_mm)} screw={liveData.screw_present} />
          </Canvas>
        </div>
        
      </div>
    </div>
  );
}

// 렌더링 파트
function DigitalTwin({ gap, screw }) {
  const isDefect = gap > 0.1;
  const visualGap = isDefect ? gap * 0.8 : 0; 
  const tiltAngle = isDefect ? 0.1 : 0; 

  return (
    <group position={[0, -0.3, 0]}>
      {/* 1. 하단 베이스 철판 */}
      <mesh position={[0, 0.2, 0]}>
        <boxGeometry args={[3, 0.4, 2.5]} />
        <meshStandardMaterial color="#334155" roughness={0.7} />
      </mesh>

      {/* 2. 결합 힌지 스택  */}
      <mesh position={[0, 0.5, 0]}>
        <boxGeometry args={[2, 0.2, 1.5]} />
        <meshStandardMaterial color={isDefect ? '#f59e0b' : '#3b82f6'} roughness={0.5} />
      </mesh>

      {/* 3. 타겟 나사  */}
      {screw ? (
        // 💡 나사가 힌지스택  Y축(0.6)을 기본으로 잡음
        <group position={[0, 0.6 + visualGap, 0]} rotation={[tiltAngle, 0, tiltAngle]}>
          
          {/* 나사 머리  */}
          <mesh position={[0, 0.05, 0]}>
            <cylinderGeometry args={[0.25, 0.25, 0.1, 32]} />
            <meshStandardMaterial color="#e2e8f0" metalness={0.9} roughness={0.1} />
          </mesh>
          
          {/* 나사 몸통  */}
          <mesh position={[0, -0.2, 0]}>
            <cylinderGeometry args={[0.1, 0.1, 0.4, 32]} />
            <meshStandardMaterial color="#94a3b8" metalness={0.8} roughness={0.3} />
          </mesh>

          {/* 단차 불량 라벨 */}
          {isDefect && (
            <Html distanceFactor={4} position={[0, 0.3, 0]} center>
              <div style={{ background: '#f59e0b', color: '#000', padding: '4px 8px', borderRadius: '4px', fontWeight: 'bold', fontSize: '13px', whiteSpace: 'nowrap', border: '2px solid #b45309', boxShadow: '0 4px 6px rgba(0,0,0,0.3)' }}>
                ⚠️ 나사 덜 박힘 (+{gap}mm)
              </div>
            </Html>
          )}
        </group>
      ) : (
        // 💡 나사 누락 시
        <Html distanceFactor={4} position={[0, 0.7, 0]} center>
          <div style={{ background: '#ef4444', color: '#fff', padding: '4px 8px', borderRadius: '4px', fontWeight: 'bold', fontSize: '13px', whiteSpace: 'nowrap', border: '2px solid #7f1d1d', boxShadow: '0 4px 6px rgba(0,0,0,0.3)' }}>
            🚨 나사 누락 (MISSING)
          </div>
        </Html>
      )}
    </group>
  );
}