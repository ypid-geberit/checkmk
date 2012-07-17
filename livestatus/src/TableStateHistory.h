// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef TableStateHistory_h
#define TableStateHistory_h

#include <map>
#include <time.h>
#include "config.h"
#include "Table.h"
#include "string.h"
#include "LogEntry.h"
#include "TableStateHistory.h"
#include "Query.h"
#include "logger.h"
#include "nagios.h"

class Logfile;

typedef int Value;
typedef pair<string, string> HostServiceKey;

class LessThan
{
public:
    bool operator()(const HostServiceKey& lhs, const HostServiceKey& rhs)
    {
        if (lhs.first < rhs.first)
            return true;
        if (lhs.first > rhs.first)
            return false;
        return lhs.second < rhs.second;
    }
};

class HostServiceState{
public:
	time_t  _time;
	time_t  _from;
	time_t  _until;
	time_t  _duration;
	int     _attempt;
	int     _hard_state; // true: hard, false: soft
	int     _state;
	char*   _state_type;
	char*   _downtime_state;
	int     _in_downtime;
	char*   _notification_period;
	int     _in_notification_period;

	LogEntry* _log_ptr;
	char*   _debug_info;

    host      *_host;
    service   *_service;

	HostServiceState()
	: _state_type(""){};
};

typedef map<HostServiceKey, HostServiceState, LessThan> SLA_Info;

class TableStateHistory : public Table
{

public:
    TableStateHistory();
    ~TableStateHistory();
    const char *name() { return "statehist"; }
    const char *prefixname() { return "statehist"; }
    bool isAuthorized(contact *ctc, void *data);
    void handleNewMessage(Logfile *logfile, time_t since, time_t until, unsigned logclasses);
    void answerQuery(Query *query);
    Column *column(const char *colname); // override in order to handle current_
    void updateHostServiceState(Query &query, LogEntry &entry, HostServiceState &state, bool only_update, bool force_process);

private:
   bool answerQuery(Query *, Logfile *, time_t, time_t);
   SLA_Info* sla_info;
};


class ProcessDataSet{
private:
	bool   _do_nothing;
	bool   _already_sent;
	Query* _query;

	HostServiceState* _hs_state;
public:
	ProcessDataSet(Query *query, HostServiceState *hs_state, bool do_nothing)
	{
		_query = query;
		_hs_state = hs_state;
		_do_nothing = do_nothing;
		_already_sent = false;
	}
	bool process(){
		if( _do_nothing )
			return false;
		if( _already_sent == true )
			return false;
		else{
			_query->processDataset(_hs_state);
			_hs_state->_from = _hs_state->_until;
			_already_sent = true;
			return true;
		}
	};
};


#endif // TableStateHistory_h
