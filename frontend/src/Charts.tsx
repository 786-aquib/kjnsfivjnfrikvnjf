import {ResponsiveContainer,LineChart,Line,XAxis,YAxis,CartesianGrid,Tooltip,BarChart,Bar,ReferenceLine,Cell} from 'recharts';
import type {Daily,Row} from './types';
import {clock,dateLabel,number} from './api';

export function ProfileChart({rows,actuals}:{rows:Row[];actuals:boolean}) {
  if (!rows || rows.length === 0) {
    return <div className="chart chart-empty">No delivery intervals available for this date.</div>;
  }
  return <div className="chart" role="img" aria-label="Wind generation in MW. Green points are exact forecast timestamps. Blue line shows actuals when enabled. All values are available in the interval table.">
    <ResponsiveContainer width="100%" height="100%"><LineChart data={rows} margin={{top:18,right:22,bottom:10,left:4}} accessibilityLayer>
      <CartesianGrid vertical={false} stroke="#e8ece6" strokeDasharray="3 4"/>
      <XAxis dataKey="startTime" tickFormatter={clock} interval={7} axisLine={false} tickLine={false} tick={{fill:'#6d7973',fontSize:12}} dy={10}/>
      <YAxis width={62} tickFormatter={v=>number(Number(v))} axisLine={false} tickLine={false} tick={{fill:'#6d7973',fontSize:12}}/>
      <Tooltip content={({active,payload,label})=>{
        if(!active || !payload?.length) return null;
        const row = payload[0]?.payload as Row | undefined;
        if (!row) return null;
        return <div className="chart-tooltip">
          <strong>{dateLabel(String(label))} · {clock(String(label))} GMT</strong>
          <p>Forecast <b>{number(row.forecast)} MW</b></p>
          {actuals&&<p>Actual <b>{number(row.actual)} MW</b></p>}
          <small>{row.publishTime?`Published ${dateLabel(row.publishTime)} at ${clock(row.publishTime)} GMT`:'No eligible forecast at this timestamp'}</small>
        </div>;
      }}/>
      {actuals&&<Line type="linear" dataKey="actual" stroke="#5e81a7" strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false}/>}
      <Line dataKey="forecast" stroke="#21765b" strokeWidth={2} dot={{r:3.8,fill:'#21765b',stroke:'#fff',strokeWidth:1.2}} activeDot={{r:6}} connectNulls={false} isAnimationActive={false}/>
    </LineChart></ResponsiveContainer>
  </div>;
}

export function DailyChart({days}:{days:Daily[]}) {
  if (!days || days.length === 0) {
    return <div className="chart chart-empty">No daily accuracy results available.</div>;
  }
  return <div className="chart" role="img" aria-label="Daily mean absolute error in MW by decision date. Values are also in the daily results table."><ResponsiveContainer width="100%" height="100%"><BarChart data={days} margin={{top:18,right:20,bottom:10,left:4}} accessibilityLayer>
    <CartesianGrid vertical={false} stroke="#e8ece6" strokeDasharray="3 4"/><XAxis dataKey="decisionDate" tickFormatter={s=>typeof s==='string'&&s.length>=10?s.slice(8):String(s)} axisLine={false} tickLine={false} tick={{fill:'#6d7973',fontSize:12}}/><YAxis width={62} axisLine={false} tickLine={false} tick={{fill:'#6d7973',fontSize:12}}/>
    <Tooltip formatter={value=>[`${number(Number(value))} MW`,'Mean absolute error']} labelFormatter={label=>`Decision ${dateLabel(String(label))}`} contentStyle={{border:'1px solid #e1e7de',borderRadius:10}}/>
    <Bar dataKey="mae" fill="#37846b" radius={[3,3,0,0]} maxBarSize={28} isAnimationActive={false}/>
  </BarChart></ResponsiveContainer></div>;
}

export function ErrorChart({rows}:{rows:Row[]}) {
  const pairs = (rows || []).filter(r => r.error !== null);
  if (pairs.length === 0) {
    return <div className="chart short chart-empty">No matched forecast-actual pairs for this day.</div>;
  }
  return <div className="chart short" role="img" aria-label="Signed forecast errors. Positive means wind was overforecast. Values appear in the interval table."><ResponsiveContainer width="100%" height="100%"><BarChart data={pairs} margin={{top:12,right:20,bottom:10,left:4}} accessibilityLayer>
    <CartesianGrid vertical={false} stroke="#e8ece6" strokeDasharray="3 4"/><XAxis dataKey="startTime" tickFormatter={clock} interval={3} axisLine={false} tickLine={false} tick={{fill:'#6d7973',fontSize:12}}/><YAxis width={62} axisLine={false} tickLine={false} tick={{fill:'#6d7973',fontSize:12}}/><ReferenceLine y={0} stroke="#8e9c91"/>
    <Tooltip labelFormatter={s=>`${clock(String(s))} GMT`} formatter={v=>[`${number(Number(v))} MW`,'Forecast − actual']}/>
    <Bar dataKey="error" isAnimationActive={false}>{pairs.map(r=><Cell key={r.startTime} fill={r.error !== null && r.error > 0 ? '#b27735' : '#38836c'}/>)}</Bar>
  </BarChart></ResponsiveContainer></div>;
}

